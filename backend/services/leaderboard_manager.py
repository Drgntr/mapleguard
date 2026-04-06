"""
Leaderboard Manager — Background task launcher for the leaderboard pipeline.

Wraps scan → enrich → watch scripts as async background tasks
that can be safely launched from main.py lifespan.

Pipeline:
  1. Scan all existing NFT transfers from Routescan API (one-shot at startup)
  2. Enrich all un-enriched chars/items via Open API + proxy pool (continuous)
  3. Watch for new mints in real-time and auto-enrich them (continuous)
"""

import asyncio
import httpx
import time
import sys
from datetime import datetime
from typing import Optional

try:
    from sqlalchemy import select, func
except ImportError:
    select = None
    func = None

# ── Shared helpers ─────────────────────────────────────────────────────────

async def _ensure_db_tables():
    """Ensure all DB tables exist."""
    from db.database import async_session, engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _get_sync_state(key: str, default: str = "") -> str:
    from db.database import SyncState, async_session
    async with async_session() as session:
        row = (await session.execute(select(SyncState).where(SyncState.key == key))).scalar_one_or_none()
        return row.value if row else default


async def _save_sync_state(key: str, value: str):
    from db.database import SyncState, async_session
    async with async_session() as session:
        row = (await session.execute(select(SyncState).where(SyncState.key == key))).scalar_one_or_none()
        if row:
            row.value = value
        else:
            session.add(SyncState(key=key, value=value))
        await session.commit()


# ── 1. Historical Scan (one-shot at startup) ─────────────────────────────

async def run_full_scan(nft_type: str = "all", limit_pages: int = 0):
    """
    Scan historic NFT mints from Routescan API and save to nft_mint_lookup.
    Uses proxy pool for rate-limit avoidance.
    If nft_type == "all", scans both chars and items.
    Runs once at startup.

    Args:
        nft_type: "all", "character", or "item"
        limit_pages: max pages to scan (0 = unlimited)
    """
    await _ensure_db_tables()

    from db.database import NftMintLookup, MintEvent, async_session
    from config import get_settings
    from services.proxy_pool import proxy_pool
    settings = get_settings()

    BASE_URL = "https://api.routescan.io/v2/network/mainnet/evm/68414"
    PAGE_LIMIT = 100

    targets = []
    if nft_type in ("all", "character"):
        targets.append(("character", settings.CHARACTER_NFT))
    if nft_type in ("all", "item"):
        targets.append(("item", settings.ITEM_NFT))

    for type_name, contract in targets:
        prefix = f"[Scan-{type_name}]"
        print(f"{prefix} Starting full historical scan...")

        # Load proxy pool
        proxy_pool.load()
        print(f"{prefix} Proxy pool status: {proxy_pool.status()}")

        # Check for resume
        cursor_url = await _get_sync_state(f"scan_{type_name}s_cursor")
        page_num = int(await _get_sync_state(f"scan_{type_name}s_page") or "0")

        if not cursor_url:
            cursor_url = f"{BASE_URL}/erc721-transfers?tokenAddress={contract}&limit={PAGE_LIMIT}"
            print(f"{prefix} Starting from beginning...")
        else:
            print(f"{prefix} Resuming from page ~{page_num}...")

        items_on_page = 0
        t0 = time.time()

        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            while cursor_url:
                page_num += 1
                if limit_pages and page_num > limit_pages:
                    print(f"{prefix} Page limit reached ({limit_pages})")
                    break

                # Try with proxy first, fallback to direct
                resp = None
                proxy_url = proxy_pool.get_proxy()
                retries = 3

                for attempt in range(retries):
                    try:
                        extra = {"proxy": proxy_url} if (proxy_url and attempt == 0) else {}
                        resp = await client.get(cursor_url, timeout=15.0, **extra)
                        if resp.status_code == 429:
                            if proxy_url and attempt == 0:
                                proxy_pool.report_failure(proxy_url, cooldown=60)
                            wait = 5 * (attempt + 1)
                            print(f"{prefix} Rate limited — waiting {wait}s (attempt {attempt+1}/{retries})")
                            await asyncio.sleep(wait)
                            proxy_url = proxy_pool.get_proxy()
                            page_num -= 1
                            continue
                        if resp.status_code != 200:
                            print(f"{prefix} HTTP {resp.status_code} — stopping")
                            resp = None
                            break
                        if proxy_url and attempt == 0:
                            proxy_pool.report_success(proxy_url)
                        break  # Success
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        print(f"{prefix} Request error (attempt {attempt+1}/{retries}): {e}")
                        if proxy_url and attempt == 0:
                            proxy_pool.report_failure(proxy_url, cooldown=30)
                        await asyncio.sleep(3)
                        proxy_url = proxy_pool.get_proxy()

                if resp is None and page_num < limit_pages:
                    print(f"{prefix} All retries failed — stopping scan")
                    break
                if resp is None:
                    continue

                try:
                    data = resp.json()
                    items = data.get("items", [])
                    if not items:
                        print(f"{prefix} No items — done!")
                        break

                    link = data.get("link", {})
                    next_path = link.get("next") if isinstance(link, dict) else None
                    cursor_url = f"https://api.routescan.io{next_path}" if next_path else ""

                    # Insert into DB
                    new_count = 0
                    for item in items:
                        token_id = str(item.get("tokenId", ""))
                        if not token_id:
                            continue
                        from_addr = item.get("from", "").lower()
                        block = int(item.get("blockNumber", 0) or item.get("block", 0))

                        ts = 0
                        created_at = item.get("createdAt", "")
                        if created_at:
                            try:
                                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                                ts = int(dt.timestamp())
                            except Exception:
                                pass

                        async with async_session() as session:
                            exists = (await session.execute(
                                select(NftMintLookup.id).where(NftMintLookup.token_id == token_id)
                            )).scalar_one_or_none()
                            if not exists:
                                session.add(NftMintLookup(
                                    token_id=token_id, nft_type=type_name,
                                    minter=from_addr, block_number=block,
                                ))
                                session.add(MintEvent(
                                    token_id=token_id, nft_type=type_name,
                                    minter=from_addr, block_number=block,
                                    timestamp=ts, enriched=False, retry_count=0,
                                ))
                                await session.commit()
                                new_count += 1

                    items_on_page += len(items)
                    elapsed = time.time() - t0
                    rate = page_num / elapsed if elapsed > 0 else 0
                    if page_num % 20 == 0 or items_on_page % 500 < PAGE_LIMIT:
                        print(f"{prefix} Page {page_num:,} | "
                              f"Items: {items_on_page:,} | New: {new_count} | "
                              f"{rate:.1f} pg/s | Proxies: {proxy_pool.status()}")

                    await _save_sync_state(f"scan_{type_name}s_cursor", cursor_url)
                    await _save_sync_state(f"scan_{type_name}s_page", str(page_num))
                    await _save_sync_state(f"scan_{type_name}s_last_block",
                                           str(block) if items and items_on_page else "0")

                    await asyncio.sleep(0.3)

                except asyncio.CancelledError:
                    print(f"{prefix} Cancelled at page {page_num}")
                    break
                except Exception as e:
                    print(f"{prefix} Error page {page_num}: {e}")
                    await asyncio.sleep(3)

        print(f"{prefix} Done! {items_on_page:,} items processed.")


# ── 2. Enrichment (continuous) ──────────────────────────────────────────

async def run_enrichment(nft_type: str, batch_size: int = 30):
    """
    Continuously enrich chars or items: find unenriched mint IDs,
    fetch from Open API (with proxy), save snapshots.
    """
    await _ensure_db_tables()

    from db.database import NftMintLookup, MintEvent, async_session
    from config import get_settings
    from services.proxy_pool import proxy_pool
    from services.combat_power_engine import CombatPowerEngine, _get_stat_total

    settings = get_settings()
    prefix = f"[Enrich-{nft_type}]"
    proxy_pool.load()
    print(f"{prefix} Proxy pool status: {proxy_pool.status()}")

    table = NftMintLookup
    snapshot_model = None
    if nft_type == "character":
        from db.database import CharacterSnapshot
        snapshot_model = CharacterSnapshot
    else:
        from db.database import ItemSnapshot
        snapshot_model = ItemSnapshot

    print(f"{prefix} Starting (batch_size={batch_size})...")

    while True:
        try:
            # Find unenriched token IDs
            async with async_session() as session:
                mint_q = select(table.token_id, table.minter).where(table.nft_type == nft_type)
                all_mints = (await session.execute(mint_q)).all()

                enriched_q = select(snapshot_model.token_id)
                enriched_set = set((r[0] for r in (await session.execute(enriched_q)).all()))

            pending = [(m[0], m[1]) for m in all_mints if m[0] not in enriched_set]
            if not pending:
                await asyncio.sleep(60)  # check again in 1 min
                continue

            print(f"{prefix} {len(pending)} items pending enrichment...")

            # Process in batches
            async with httpx.AsyncClient(timeout=30.0) as client:
                sem = asyncio.Semaphore(4)

                async def enrich_one(token_id: str, minter: str):
                    async with sem:
                        return await _enrich_single(
                            client, token_id, minter, nft_type,
                            settings, snapshot_model,
                            CombatPowerEngine, _get_stat_total,
                            proxy_pool
                        )

                batch = pending[:batch_size]
                tasks = [enrich_one(tid, m) for tid, m in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                ok = sum(1 for r in results if r and not isinstance(r, Exception))
                skipped = sum(1 for r in results if not r and not isinstance(r, Exception))
                errs = sum(1 for r in results if isinstance(r, Exception))
                print(f"{prefix} Batch done: {ok} enriched, {skipped} skipped, {errs} errors")

            await asyncio.sleep(2)  # brief pause between batches

        except asyncio.CancelledError:
            print(f"{prefix} Cancelled.")
            break
        except Exception as e:
            print(f"{prefix} Error: {e}")
            await asyncio.sleep(30)


async def _enrich_single(client, token_id, minter, nft_type, settings,
                         snapshot_model, CombatPowerEngine, _get_stat_total, proxy_pool):
    """Enrich a single NFT via Open API with retry and proxy rotation."""
    if nft_type == "character":
        url = f"{settings.MSU_OPENAPI_BASE}/characters/by-token-id/{token_id}"
    else:
        url = f"{settings.MSU_OPENAPI_BASE}/items/by-token-id/{token_id}"

    headers = {"accept": "application/json", "x-nxopen-api-key": settings.MSU_OPENAPI_KEY}

    max_retries = 3
    backoffs = [5, 15, 60]

    for attempt in range(max_retries):
        proxy_url = proxy_pool.get_proxy()
        extra = {"proxy": proxy_url} if proxy_url else {}

        try:
            resp = await client.get(url, headers=headers, timeout=30, **extra)
            if resp.status_code == 429:
                if proxy_url:
                    proxy_pool.report_failure(proxy_url, cooldown=30)
                await asyncio.sleep(backoffs[min(attempt, len(backoffs)-1)])
                continue
            if resp.status_code != 200:
                if proxy_url:
                    proxy_pool.report_failure(proxy_url)
                await asyncio.sleep(backoffs[min(attempt, len(backoffs)-1)])
                continue
            if proxy_url:
                proxy_pool.report_success(proxy_url)

            body = resp.json()
            if not body.get("success") or not body.get("data"):
                return None

            data_obj = body["data"]
            inner_key = "character" if nft_type == "character" else "item"
            inner_data = data_obj.get(inner_key, data_obj)

            import json

            if nft_type == "character":
                from models.character import CharacterListing
                from db.database import CharacterSnapshot, async_session

                char_obj = CharacterListing.from_openapi(inner_data)
                ap = inner_data.get("apStat", {})
                cp_val = CombatPowerEngine.calculate_cp(
                    primary_stat=_get_stat_total(ap, "str"),
                    secondary_stat=_get_stat_total(ap, "dex"),
                    total_att=max(_get_stat_total(ap, "pad"), _get_stat_total(ap, "attackPower"), _get_stat_total(ap, "mad")),
                    damage_pct=_get_stat_total(ap, "damage"),
                    boss_damage_pct=_get_stat_total(ap, "boss_monster_damage"),
                    crit_damage_pct=_get_stat_total(ap, "critical_damage"),
                    crit_damage_base=0.0,
                )

                ap_stats = json.dumps(char_obj.ap_stats.model_dump(), ensure_ascii=False) if char_obj.ap_stats else None

                async with async_session() as session:
                    existing = (await session.execute(
                        select(CharacterSnapshot).where(CharacterSnapshot.token_id == token_id)
                    )).scalar_one_or_none()
                    if existing:
                        existing.combat_power = int(cp_val)
                        existing.char_att = _get_stat_total(ap, "pad")
                        existing.char_matt = _get_stat_total(ap, "mad")
                        existing.name = char_obj.name or existing.name
                        existing.class_name = char_obj.class_name or existing.class_name
                        existing.job_name = char_obj.job_name or existing.job_name
                        existing.class_code = char_obj.class_code or existing.class_code
                        existing.job_code = char_obj.job_code or existing.job_code
                        existing.level = char_obj.level or existing.level
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
                            combat_power=int(cp_val) if cp_val > 0 else 0,
                            char_att=_get_stat_total(ap, "pad"),
                            char_matt=_get_stat_total(ap, "mad"),
                            ap_stats_json=ap_stats,
                            image_url=char_obj.image_url,
                            source="openapi",
                        ))
                    await session.commit()

                # Update MintEvent enriched flag
                async with async_session() as session:
                    evt = (await session.execute(
                        select(MintEvent).where(MintEvent.token_id == token_id)
                    )).scalar_one_or_none()
                    if evt and not evt.enriched:
                        evt.enriched = True
                        evt.retry_count = attempt
                        await session.commit()

            else:
                from models.item import ItemListing
                from db.database import ItemSnapshot, async_session

                item_obj = ItemListing.from_openapi(inner_data)
                enh = inner_data.get("enhance", {})
                sf = enh.get("starforce", {}).get("enhanced", 0) or 0
                stats = json.dumps(item_obj.stats.model_dump(), ensure_ascii=False) if item_obj.stats else None

                pg = 0
                bpg = 0
                try:
                    if enh.get("potential"):
                        pg = enh["potential"].get("option1", {}).get("grade", 0) or 0
                    if enh.get("bonusPotential"):
                        bpg = enh["bonusPotential"].get("option1", {}).get("grade", 0) or 0
                except Exception:
                    pass

                async with async_session() as session:
                    existing = (await session.execute(
                        select(ItemSnapshot).where(ItemSnapshot.token_id == token_id)
                    )).scalar_one_or_none()
                    if existing:
                        existing.starforce = sf
                        existing.potential_grade = pg
                    else:
                        session.add(ItemSnapshot(
                            token_id=token_id,
                            asset_key=inner_data.get("assetKey"),
                            name=item_obj.name or "",
                            category_no=item_obj.category_no,
                            category_label=item_obj.category_label,
                            item_id=item_obj.item_id,
                            starforce=sf,
                            enable_starforce=item_obj.enable_starforce,
                            potential_grade=pg,
                            bonus_potential_grade=bpg,
                            stats_json=stats,
                            image_url=item_obj.image_url,
                            source="openapi",
                        ))
                    await session.commit()

            return True

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  [{nft_type} RETRY {attempt+1}/{max_retries}] {token_id}: {e}")
                await asyncio.sleep(backoffs[attempt])
            else:
                print(f"  [{nft_type} ERR] {token_id} after {max_retries} retries: {e}")
                # Mark retry_count on MintEvent
                try:
                    async with async_session() as session:
                        evt = (await session.execute(
                            select(MintEvent).where(MintEvent.token_id == token_id)
                        )).scalar_one_or_none()
                        if evt:
                            evt.retry_count = max_retries
                            await session.commit()
                except Exception:
                    pass

    return None


# ── 3. Live Mint Watchers ───────────────────────────────────────────────

async def run_mint_watcher(nft_type: str, poll_interval: int = 5):
    """
    Poll blockchain for new mints (Transfer from 0x0) on the NFT contract.
    Auto-enrich newly minted NFTs.
    """
    await _ensure_db_tables()

    from db.database import NftMintLookup, MintEvent, async_session
    from config import get_settings
    settings = get_settings()

    if nft_type == "character":
        contract = settings.CHARACTER_NFT
    else:
        contract = settings.ITEM_NFT

    RPC_URL = settings.RPC_URL
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    ZERO_ADDR = "0x0000000000000000000000000000000000000000"
    prefix = f"[Watch-{nft_type}]"

    # Get last watched block
    last_block_str = await _get_sync_state(f"watch_{nft_type}s_last_block")
    last_block = int(last_block_str) if last_block_str.isdigit() else 0

    print(f"{prefix} Starting (last block: {last_block:,}, poll: {poll_interval}s)")

    async with httpx.AsyncClient(timeout=20.0) as client:
        while True:
            try:
                # Get current block
                r = await client.post(RPC_URL, json={
                    "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1,
                })
                head = int(r.json().get("result", "0x0"), 16)
                if head == 0 or head <= last_block:
                    await asyncio.sleep(poll_interval)
                    continue

                # Fetch Transfer(from=0x0) logs — batch up to 1000 blocks per request
                from_block = last_block + 1
                while from_block <= head:
                    to_block = min(from_block + 999, head)

                    payload = {
                        "jsonrpc": "2.0",
                        "method": "eth_getLogs",
                        "params": [{
                            "address": contract,
                            "topics": [TRANSFER_TOPIC, "0x" + "0" * 64],
                            "fromBlock": hex(from_block),
                            "toBlock": hex(to_block),
                        }],
                        "id": 1,
                    }
                    r = await client.post(RPC_URL, json=payload, timeout=20.0)
                    logs = r.json().get("result", []) or []

                    for log in logs:
                        topics = log.get("topics", [])
                        if len(topics) != 4:
                            continue
                        token_id = str(int(topics[3], 16))
                        minter = "0x" + topics[2][2:].lower().zfill(40)[-40:]
                        block_num = int(log.get("blockNumber", "0x0"), 16)

                        async with async_session() as session:
                            exists = (await session.execute(
                                select(NftMintLookup.id).where(NftMintLookup.token_id == token_id)
                            )).scalar_one_or_none()
                            if not exists:
                                session.add(NftMintLookup(
                                    token_id=token_id, nft_type=nft_type,
                                    minter=minter, block_number=block_num,
                                ))
                                session.add(MintEvent(
                                    token_id=token_id, nft_type=nft_type,
                                    minter=minter, block_number=block_num,
                                    timestamp=int(time.time()), enriched=False, retry_count=0,
                                ))
                                await session.commit()
                                print(f"{prefix} NEW MINT: {token_id} | minter: {minter[:10]}...")

                    from_block = to_block + 1

                last_block = head
                await _save_sync_state(f"watch_{nft_type}s_last_block", str(head))

            except asyncio.CancelledError:
                print(f"{prefix} Cancelled.")
                break
            except Exception as e:
                print(f"{prefix} Error: {e}")
                await asyncio.sleep(10)

            await asyncio.sleep(poll_interval)


# ── Public API for main.py ──────────────────────────────────────────────

async def scan_all_task(limit_pages: int = 0):
    """One-shot scan of all NFTs at startup."""
    await run_full_scan("all", limit_pages=limit_pages)


async def enrich_chars_task(batch_size: int = 30):
    """Continuous char enrichment."""
    await run_enrichment("character", batch_size=batch_size)


async def enrich_items_task(batch_size: int = 30):
    """Continuous item enrichment."""
    await run_enrichment("item", batch_size=batch_size)


async def watch_chars_task():
    """Live char mint watcher."""
    await run_mint_watcher("character")


async def watch_items_task():
    """Live item mint watcher."""
    await run_mint_watcher("item")
