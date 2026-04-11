"""
enrich_characters.py — Enrich all minted characters with real stats from MSU Open API.

Reads token_ids from nft_mint_lookup that don't yet have a character_snapshots record.
Calls Open API with proxy rotation, computes CP, saves full snapshot to DB.

Usage:
    python scripts/enrich_characters.py
    python scripts/enrich_characters.py --batch-size 30
    python scripts/enrich_characters.py --resume
"""

import asyncio
import httpx
import json
import os
import signal
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from db.database import (
    NftMintLookup, CharacterSnapshot, SyncState,
    async_session, engine, Base,
)
from config import get_settings
from services.proxy_pool import proxy_pool

settings = get_settings()

# ── Config ────────────────────────────────────────────────────────
BATCH_SIZE = 50          # tokens per batch before checkpoint
MAX_CONCURRENCY = 4      # concurrent API calls
RATE_LIMIT_DELAY = 0.12  # ~8 req/s (below 10 req/s Open API limit)
MAX_RETRIES = 3


async def call_openapi(session: httpx.AsyncClient, token_id: str) -> dict | None:
    """Call MSU Open API for character by token ID."""
    url = f"{settings.MSU_OPENAPI_BASE}/characters/by-token-id/{token_id}"
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
                print(f"[\nAPI {resp.status_code}] for {token_id}")
                if proxy_url:
                    proxy_pool.report_failure(proxy_url, cooldown=30)
                return None
            if proxy_url:
                proxy_pool.report_success(proxy_url)
            body = resp.json()
            if body.get("success") and body.get("data"):
                return body["data"]  # {"character": {...}}
            return None

        except Exception as e:
            if proxy_url:
                proxy_pool.report_failure(proxy_url, cooldown=30)
            print(f"\n[ERR] {token_id} attempt {attempt+1}: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2)
    return None


async def save_snapshot(char_data: dict, token_id: str, minter: str):
    """Parse character data and save snapshot to DB."""
    from models.character import CharacterListing
    from services.combat_power_engine import combat_power_engine

    char_obj = CharacterListing.from_openapi(char_data)

    # Compute CP
    combat_power = 0
    char_att = 0.0
    char_matt = 0.0
    try:
        from services.combat_power_engine import CombatPowerEngine, _get_stat_total
        ap = char_data.get("apStat", {}) or character.get("apStat", {})

        # attackPower IS the real Combat Power (전투력) in MSU API
        ap_cp_raw = ap.get("attackPower") if isinstance(ap, dict) else None
        if ap_cp_raw:
            try:
                combat_power = int(ap_cp_raw)
            except (ValueError, TypeError):
                pass

        # Fallback: derive from formula with proper stat detection
        if combat_power <= 0:
            job_name = char_data.get("common", {}).get("job", {}).get("jobName", "")
            p_key, s_key = CombatPowerEngine.detect_primary_secondary(job_name, ap)
            cp_val = CombatPowerEngine.calculate_cp(
                primary_stat=_get_stat_total(ap, p_key),
                secondary_stat=_get_stat_total(ap, s_key),
                total_att=max(_get_stat_total(ap, "pad"), _get_stat_total(ap, "mad")),
                damage_pct=_get_stat_total(ap, "damage"),
                boss_damage_pct=_get_stat_total(ap, "bossMonsterDamage", "boss_monster_damage"),
                final_damage_pct=_get_stat_total(ap, "finalDamage", "final_damage"),
                crit_damage_pct=_get_stat_total(ap, "criticalDamage", "critical_damage"),
                crit_damage_base=0.0,
            )
            combat_power = int(cp_val) if cp_val > 0 else 0

        char_att = _get_stat_total(ap, "pad")
        char_matt = _get_stat_total(ap, "mad")
    except Exception as e:
        print(f"  [CP error] {token_id}: {e}")

    ap_stats = None
    hyper_stats = None
    wearing = None
    equipped = None

    try:
        if char_obj.ap_stats:
            ap_stats = char_obj.ap_stats.model_dump()
    except Exception:
        pass

    # Try to extract raw data for JSON storage
    character = char_data.get("character", {})
    hyper_raw = character.get("hyperStat", {}) or char_data.get("hyperStat", {})
    wearing_raw = character.get("wearing", {}) or char_data.get("wearing", {})

    try:
        if hyper_raw and isinstance(hyper_raw, dict):
            hyper_stats = json.dumps(hyper_raw, ensure_ascii=False)[:500000]
    except Exception:
        pass

    try:
        if wearing_raw and isinstance(wearing_raw, dict):
            wearing = json.dumps(wearing_raw, ensure_ascii=False)[:2000000]
    except Exception:
        pass

    try:
        if char_obj.equipped_items:
            equipped = json.dumps([e.model_dump() for e in char_obj.equipped_items], ensure_ascii=False)[:1000000]
    except Exception:
        pass

    async with async_session() as session:
        existing = (await session.execute(
            select(CharacterSnapshot).where(CharacterSnapshot.token_id == token_id)
        )).scalar_one_or_none()

        if existing:
            existing.combat_power = combat_power
            existing.char_att = char_att
            existing.char_matt = char_matt
            existing.name = char_obj.name or existing.name
            existing.class_name = char_obj.class_name or existing.class_name
            existing.job_name = char_obj.job_name or existing.job_name
            existing.class_code = char_obj.class_code
            existing.job_code = char_obj.job_code
            existing.level = char_obj.level or existing.level
            existing.asset_key = char_obj.asset_key
            existing.image_url = char_obj.image_url
            if ap_stats:
                existing.ap_stats_json = json.dumps(ap_stats, ensure_ascii=False)
            if hyper_stats:
                existing.hyper_stats_json = hyper_stats
            if wearing:
                existing.wearing_json = wearing
            if equipped:
                existing.equipped_items_json = equipped
            existing.source = "openapi"
        else:
            session.add(CharacterSnapshot(
                token_id=token_id,
                asset_key=char_obj.asset_key,
                name=char_obj.name or "",
                class_name=char_obj.class_name,
                job_name=char_obj.job_name,
                class_code=char_obj.class_code,
                job_code=char_obj.job_code,
                level=char_obj.level or 0,
                combat_power=combat_power,
                char_att=char_att,
                char_matt=char_matt,
                ap_stats_json=json.dumps(ap_stats, ensure_ascii=False) if ap_stats else None,
                hyper_stats_json=hyper_stats,
                wearing_json=wearing,
                equipped_items_json=equipped,
                image_url=char_obj.image_url,
                price_wei="0",
                source="openapi",
            ))

        # Mark corresponding mint event as enriched
        stmt = (await session.execute(
            select(SyncState).where(SyncState.key == "enrich_characters_last_token")
        )).scalar_one_or_none()
        if stmt:
            stmt.value = token_id
        else:
            session.add(SyncState(key="enrich_characters_last_token", value=token_id))

        await session.commit()

    return {
        "token_id": token_id,
        "name": char_obj.name,
        "class": char_obj.class_name,
        "level": char_obj.level,
        "cp": combat_power,
    }


async def enrich_single(client, token_id: str, minter: str) -> dict | None:
    """Fetch and save single character."""
    data = await call_openapi(client, token_id)
    if not data or not data.get("character"):
        return None
    return await save_snapshot(data["character"], token_id, minter)


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
    print(f"  Character Enricher — Open API → SQLite")
    print(f"  Proxies: {ps['total']} total, {ps['available']} available")
    print(f"  Rate: ~8 req/s | Concurrency: {MAX_CONCURRENCY}")
    print(f"{'='*65}\n")

    # Get unenriched token IDs
    async with async_session() as session:
        from sqlalchemy import outerjoin

        # Get all character mint IDs
        mint_query = select(NftMintLookup.token_id, NftMintLookup.minter)\
            .where(NftMintLookup.nft_type == "character")
        mints = (await session.execute(mint_query)).all()

        # Get already-enriched token IDs
        enriched_query = select(CharacterSnapshot.token_id)
        enriched_set = set((r[0] for r in (await session.execute(enriched_query)).all()))

    mints_to_enrich = [(m[0], m[1]) for m in mints if m[0] not in enriched_set]
    print(f"  Found {len(mints_to_enrich)}/{len(mints)} characters needing enrichment\n")

    if not mints_to_enrich:
        print("  All characters are already enriched. Nothing to do.")
        return

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def enriched_with_semaphore(token_id, minter):
        async with semaphore:
            return await enrich_single(client, token_id, minter)

    t0 = time.time()
    enriched_count = 0
    skipped_count = 0
    errors = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        batch = []
        for token_id, minter in mints_to_enrich:
            if stop_flag[0]:
                break

            batch.append((token_id, minter))

            if len(batch) >= batch_size:
                tasks = [enriched_with_semaphore(tid, mint) for tid, mint in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for r in results:
                    if isinstance(r, Exception):
                        errors += 1
                    elif r:
                        enriched_count += 1
                        if enriched_count <= 5 or enriched_count % 50 == 0:
                            print(f"  [{enriched_count}] {r['name'][:20]:20s} | "
                                  f"{r['class'][:15]:15s} | Lv{r['level']:3d} | CP {r['cp']:,}")
                    else:
                        skipped_count += 1

                elapsed = time.time() - t0
                rate = enriched_count / elapsed if elapsed > 0 else 0
                sys.stdout.write(
                    f"\r  Enriched: {enriched_count:>6,}  |  Skipped: {skipped_count:>4,}  |  "
                    f"Errors: {errors:>3,}  |  {rate:.1f} chars/s  "
                )
                sys.stdout.flush()

                batch = []

                # Rate limit pause after each batch
                await asyncio.sleep(RATE_LIMIT_DELAY * len(batch))

        # Process remaining
        if batch and not stop_flag[0]:
            tasks = [enriched_with_semaphore(tid, mint) for tid, mint in batch]
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
