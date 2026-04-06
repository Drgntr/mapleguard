"""
enrich_items.py — Enrich all minted items with real stats from MSU Open API.

Reads token_ids from nft_mint_lookup that don't yet have an item_snapshots record.
Calls Open API with proxy rotation, saves full snapshot to DB.

Usage:
    python scripts/enrich_items.py
    python scripts/enrich_items.py --batch-size 50
"""

import asyncio
import httpx
import json
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from db.database import (
    NftMintLookup, ItemSnapshot, SyncState,
    async_session, engine, Base,
)
from config import get_settings
from services.proxy_pool import proxy_pool

settings = get_settings()

# ── Config ────────────────────────────────────────────────────────
BATCH_SIZE = 50
MAX_CONCURRENCY = 4
RATE_LIMIT_DELAY = 0.12
MAX_RETRIES = 3


async def call_openapi(session: httpx.AsyncClient, token_id: str) -> dict | None:
    """Call MSU Open API for item by token ID (numeric)."""
    url = f"{settings.MSU_OPENAPI_BASE}/items/by-token-id/{token_id}"
    headers = {
        "accept": "application/json",
        "x-nxopen-api-key": settings.MSU_OPENAPI_KEY,
    }

    for attempt in range(MAX_RETRIES):
        proxy_url = proxy_pool.get_proxy()
        extra = {}
        if proxy_url:
            extra = {"proxy": proxy_url}

        try:
            resp = await session.get(url, headers=headers, timeout=30, **extra)

            if resp.status_code == 429:
                wait = min(30 * (attempt + 1), 120)
                if proxy_url:
                    proxy_pool.report_failure(proxy_url, cooldown=60)
                print(f"\n[429] Rate limited — waiting {wait}s for {token_id}")
                await asyncio.sleep(wait)
                continue

            if resp.status_code != 200:
                if proxy_url:
                    proxy_pool.report_failure(proxy_url, cooldown=30)
                return None

            if proxy_url:
                proxy_pool.report_success(proxy_url)

            body = resp.json()
            if body.get("success") and body.get("data"):
                return body["data"]
            return None

        except Exception as e:
            if proxy_url:
                proxy_pool.report_failure(proxy_url, cooldown=30)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2)
    return None


async def save_snapshot(item_data: dict, token_id: str):
    """Parse item data and save snapshot to DB."""
    from models.item import ItemListing

    item_obj = ItemListing.from_openapi(item_data)

    stats = None
    potential = None
    bonus_potential = None
    attributes = None

    try:
        if item_obj.stats:
            stats = json.dumps(item_obj.stats.model_dump(), ensure_ascii=False)
    except Exception:
        pass

    try:
        if item_obj.potential:
            potential = json.dumps(item_obj.potential.model_dump(), ensure_ascii=False)
    except Exception:
        pass

    try:
        if item_obj.bonus_potential:
            bonus_potential = json.dumps(item_obj.bonus_potential.model_dump(), ensure_ascii=False)
    except Exception:
        pass

    try:
        if item_obj.attributes:
            attributes = json.dumps(
                [a.model_dump() for a in item_obj.attributes],
                ensure_ascii=False
            )[:500000]
    except Exception:
        pass

    enh = item_data.get("enhance", {})
    starforce = enh.get("starforce", {}).get("enhanced", 0) or 0

    potential_grade = 0
    bonus_potential_grade = 0
    try:
        if enh.get("potential"):
            potential_grade = enh["potential"].get("option1", {}).get("grade", 0) or 0
        if enh.get("bonusPotential"):
            bonus_potential_grade = enh["bonusPotential"].get("option1", {}).get("grade", 0) or 0
    except Exception:
        pass

    async with async_session() as session:
        existing = (await session.execute(
            select(ItemSnapshot).where(ItemSnapshot.token_id == token_id)
        )).scalar_one_or_none()

        if existing:
            existing.name = item_obj.name or existing.name
            existing.category_no = item_obj.category_no
            existing.category_label = item_obj.category_label
            existing.item_id = item_obj.item_id
            existing.starforce = starforce
            existing.potential_grade = potential_grade
            existing.bonus_potential_grade = bonus_potential_grade
            existing.asset_key = item_data.get("assetKey")
            existing.image_url = item_obj.image_url
            if stats:
                existing.stats_json = stats
            if potential:
                existing.potential_json = potential
            if bonus_potential:
                existing.bonus_potential_json = bonus_potential
            if attributes:
                existing.attributes_json = attributes
            existing.source = "openapi"
        else:
            session.add(ItemSnapshot(
                token_id=token_id,
                asset_key=item_data.get("assetKey"),
                name=item_obj.name or "",
                category_no=item_obj.category_no,
                category_label=item_obj.category_label,
                item_id=item_obj.item_id,
                starforce=starforce,
                enable_starforce=item_obj.enable_starforce,
                potential_grade=potential_grade,
                bonus_potential_grade=bonus_potential_grade,
                stats_json=stats,
                potential_json=potential,
                bonus_potential_json=bonus_potential,
                attributes_json=attributes,
                image_url=item_obj.image_url,
                price_wei="0",
                source="openapi",
            ))

        # Track progress
        row = (await session.execute(select(SyncState).where(SyncState.key == "enrich_items_last_token"))).scalar_one_or_none()
        if row:
            row.value = token_id
        else:
            session.add(SyncState(key="enrich_items_last_token", value=token_id))

        await session.commit()

    return {"token_id": token_id, "name": item_obj.name}


async def enrich_single(client, token_id: str) -> dict | None:
    data = await call_openapi(client, token_id)
    if not data or not data.get("item"):
        return None
    return await save_snapshot(data["item"], token_id)


async def run(batch_size: int = BATCH_SIZE):
    stop_flag = [False]

    def _sigint(sig, frame):
        print("\n\n[CTRL+C] Stopping...")
        stop_flag[0] = True

    signal.signal(signal.SIGINT, _sigint)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    proxy_pool.load()
    ps = proxy_pool.status()
    print(f"{'='*65}")
    print(f"  Item Enricher — Open API → SQLite")
    print(f"  Proxies: {ps['total']} total, {ps['available']} available")
    print(f"  Rate: ~8 req/s | Concurrency: {MAX_CONCURRENCY}")
    print(f"{'='*65}\n")

    # Get unenriched tokens
    async with async_session() as session:
        mint_query = select(NftMintLookup.token_id).where(NftMintLookup.nft_type == "item")
        mints = (await session.execute(mint_query)).all()
        mints = [m[0] for m in mints]

        enriched_query = select(ItemSnapshot.token_id)
        enriched_set = set((r[0] for r in (await session.execute(enriched_query)).all()))

    mints_to_enrich = [t for t in mints if t not in enriched_set]
    print(f"  Found {len(mints_to_enrich)}/{len(mints)} items needing enrichment\n")

    if not mints_to_enrich:
        print("  All items are already enriched. Nothing to do.")
        return

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def enriched_with_semaphore(token_id):
        async with semaphore:
            return await enrich_single(client, token_id)

    t0 = time.time()
    enriched_count = 0
    skipped_count = 0
    errors = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        batch = []
        for token_id in mints_to_enrich:
            if stop_flag[0]:
                break

            batch.append(token_id)

            if len(batch) >= batch_size:
                tasks = [enriched_with_semaphore(tid) for tid in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for r in results:
                    if isinstance(r, Exception):
                        errors += 1
                    elif r:
                        enriched_count += 1
                        if enriched_count <= 5 or enriched_count % 50 == 0:
                            print(f"  [{enriched_count}] {r['name'][:30]}")
                    else:
                        skipped_count += 1

                elapsed = time.time() - t0
                rate = enriched_count / elapsed if elapsed > 0 else 0
                sys.stdout.write(
                    f"\r  Enriched: {enriched_count:>6,}  |  Skipped: {skipped_count:>4,}  |  "
                    f"Errors: {errors:>3,}  |  {rate:.1f} items/s  "
                )
                sys.stdout.flush()

                batch = []
                await asyncio.sleep(RATE_LIMIT_DELAY)

        # Process remaining
        if batch and not stop_flag[0]:
            tasks = [enriched_with_semaphore(tid) for tid in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    errors += 1
                elif r:
                    enriched_count += 1
                else:
                    skipped_count += 1

    print(f"\n\n{'='*65}")
    print(f"  DONE  |  Enriched: {enriched_count:,}  |  Skipped: {skipped_count:,}  |  Errors: {errors:,}")
    print(f"{'='*65}")


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run(batch_size=args.batch_size))
