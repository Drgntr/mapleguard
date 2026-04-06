"""
Leaderboard Manager — Background task launcher for the leaderboard pipeline.

Pipeline:
  1. SCAN: Routescan API → todos os token IDs mintados (com proxy)
  2. WATCH: RPC da Henesys → novos mints em tempo real (sem proxy)
  3. POPULATE: Navigator API → detalhes completos (shared httpx client)
  4. ENRICH: Contínuo — pega novos mints e popula via Navigator
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Optional, Set

try:
    from sqlalchemy import select, func, distinct
except ImportError:
    select = None
    func = None
    distinct = None

from services.combat_power_engine import _get_stat_total

NAV_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
}


# ── Shared helpers ─────────────────────────────────────────────────────────

async def _ensure_db_tables():
    from db.database import async_session, engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _get_sync_state(key: str, default: str = "") -> str:
    from db.database import SyncState, async_session
    async with async_session() as session:
        row = (await session.execute(
            select(SyncState).where(SyncState.key == key)
        )).scalar_one_or_none()
        return row.value if row else default


async def _save_sync_state(key: str, value: str):
    from db.database import SyncState, async_session
    async with async_session() as session:
        row = (await session.execute(
            select(SyncState).where(SyncState.key == key)
        )).scalar_one_or_none()
        if row:
            row.value = value
        else:
            session.add(SyncState(key=key, value=value))
        await session.commit()


# ── 1. SCAN: Historical mints via Routescan (com proxy) ────────────────────

async def run_full_scan(nft_type: str = "all", limit_pages: int = 0):
    """Scan historic mint events do contrato de Character NFT via Routescan API."""
    await _ensure_db_tables()

    from db.database import NftMintLookup, MintEvent, async_session
    from config import get_settings
    from services.proxy_pool import proxy_pool
    proxy_pool.load()
    print(f"[Scan-{nft_type}] Proxy pool status: {proxy_pool.status()}")

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
        print(f"{prefix} Starting full historical scan from Routescan...")

        cursor_url = await _get_sync_state(f"scan_{type_name}s_cursor")
        page_num = int(await _get_sync_state(f"scan_{type_name}s_page") or "0")

        if not cursor_url:
            cursor_url = f"{BASE_URL}/erc721-transfers?tokenAddress={contract}&limit={PAGE_LIMIT}"
            print(f"{prefix} Starting from beginning...")
        else:
            print(f"{prefix} Resuming from page ~{page_num}...")

        total_items = 0
        t0 = time.time()

        base_proxy = proxy_pool.get_proxy()
        client_kwargs = {"verify": False, "timeout": 15.0}
        if base_proxy:
            if not base_proxy.startswith(("http://", "https://")):
                base_proxy = f"http://{base_proxy}"
            client_kwargs["proxy"] = base_proxy

        async with httpx.AsyncClient(**client_kwargs) as client:
            while cursor_url:
                page_num += 1
                if limit_pages and page_num > limit_pages:
                    break

                resp = None
                success = False

                for attempt in range(3):
                    try:
                        resp = await client.get(cursor_url, timeout=15.0)

                        if resp.status_code == 429:
                            if base_proxy:
                                proxy_pool.report_failure(base_proxy, cooldown=60)
                            wait = 10 * (attempt + 1)
                            print(f"{prefix} Rate limited — waiting {wait}s")
                            await asyncio.sleep(wait)
                            base_proxy = proxy_pool.get_proxy()
                            page_num -= 1
                            continue

                        if resp.status_code != 200:
                            print(f"{prefix} HTTP {resp.status_code} — stopping")
                            cursor_url = ""
                            break

                        if base_proxy:
                            proxy_pool.report_success(base_proxy)
                        success = True
                        break

                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        print(f"{prefix} Request error (attempt {attempt+1}/3): {e}")
                        if base_proxy:
                            proxy_pool.report_failure(base_proxy, cooldown=30)
                        base_proxy = proxy_pool.get_proxy()
                        await asyncio.sleep(5)

                if not cursor_url or not success:
                    break

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    print(f"{prefix} No more items — done!")
                    break

                link = data.get("link", {})
                next_path = link.get("next") if isinstance(link, dict) else None
                cursor_url = f"https://api.routescan.io{next_path}" if next_path else ""

                new_count = 0
                for item in items:
                    token_id = str(item.get("tokenId", "")).strip().rstrip("\n")
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

                    is_mint = from_addr == "0x0000000000000000000000000000000000000000"

                    async with async_session() as session:
                        exists = (await session.execute(
                            select(NftMintLookup.id).where(NftMintLookup.token_id == token_id)
                        )).scalar_one_or_none()
                        if not exists and is_mint:
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

                total_items += len(items)
                elapsed = max(time.time() - t0, 0.1)
                if page_num % 10 == 0 or new_count > 0:
                    print(f"{prefix} Page {page_num} | Items: {total_items} | New mints: {new_count} | {total_items/elapsed:.0f} pg/s | Proxies: {proxy_pool.status()}")

                await _save_sync_state(f"scan_{type_name}s_cursor", cursor_url)
                await _save_sync_state(f"scan_{type_name}s_page", str(page_num))
                await asyncio.sleep(0.5)

        print(f"{prefix} Done! {total_items} items processed.")


# ── 2. WATCH: Real-time mint watcher via RPC ─────────────────────────────

async def run_mint_watcher(nft_type: str, poll_interval: int = 10):
    """Poll JSON-RPC para novos mints (Transfer from 0x0)."""
    await _ensure_db_tables()

    from db.database import NftMintLookup, MintEvent, async_session
    from config import get_settings
    settings = get_settings()

    contract = settings.CHARACTER_NFT if nft_type == "character" else settings.ITEM_NFT
    RPC_URL = settings.RPC_URL
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    prefix = f"[Watch-{nft_type}]"

    last_block_str = await _get_sync_state(f"watch_{nft_type}s_last_block")
    last_block = int(last_block_str) if last_block_str.isdigit() else 0

    print(f"{prefix} Starting (last block: {last_block:,}, poll: {poll_interval}s)")

    async with httpx.AsyncClient(timeout=20.0) as client:
        while True:
            try:
                r = await client.post(RPC_URL, json={
                    "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1,
                })
                head = int(r.json().get("result", "0x0"), 16)
                if head == 0 or head <= last_block:
                    await asyncio.sleep(poll_interval)
                    continue

                from_block = last_block + 1
                while from_block <= head:
                    to_block = min(from_block + 999, head)

                    r = await client.post(RPC_URL, json={
                        "jsonrpc": "2.0",
                        "method": "eth_getLogs",
                        "params": [{
                            "address": contract,
                            "topics": [TRANSFER_TOPIC, "0x" + "0" * 64],
                            "fromBlock": hex(from_block),
                            "toBlock": hex(to_block),
                        }],
                        "id": 1,
                    }, timeout=20.0)
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
                break
            except Exception as e:
                print(f"{prefix} Error: {e}")
                await asyncio.sleep(10)

            await asyncio.sleep(poll_interval)


# ── 3. Token metadata & Navigator enrichment ───────────────────────────────

async def _token_uri_metadata(token_id: str) -> Optional[str]:
    """Fetch character name from on-chain tokenURI."""
    try:
        tid_num = int(token_id.strip())
        tid_hex = hex(tid_num)[2:].zfill(64)

        from config import get_settings
        settings = get_settings()

        payload = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{
                "to": settings.CHARACTER_NFT,
                "data": "0xc87b56dd" + tid_hex,
            }, "latest"],
            "id": 1,
        }

        async with httpx.AsyncClient(timeout=15.0) as rpc_client:
            resp = await rpc_client.post(settings.RPC_URL, json=payload)
            result = resp.json().get("result", "")

        if not result or result == "0x":
            return None

        data = result[2:]
        offset_bytes = int(data[:64], 16)
        str_start_hex = 64 + offset_bytes * 2
        raw_bytes = bytes.fromhex(data[str_start_hex:])
        null_idx = raw_bytes.index(b"\x00") if b"\x00" in raw_bytes else len(raw_bytes)
        uri = raw_bytes[:null_idx].decode("utf-8").strip()

        if uri.startswith("ipfs://"):
            uri = f"https://ipfs.io/ipfs/{uri[7:]}"
        elif not uri.startswith(("http://", "https://")):
            print(f"  [Metadata SKIP] {token_id}: {uri[:140]}")
            return None

        async with httpx.AsyncClient(timeout=15.0) as meta_client:
            resp2 = await meta_client.get(uri, headers={"accept": "application/json"})
            resp2.raise_for_status()
            return resp2.json().get("name", "")
    except Exception as e:
        print(f"  [Metadata ERR] {token_id}: {e}")
        return None


async def _search_asset_key(char_name: str, nav_client: httpx.AsyncClient) -> Optional[dict]:
    """Search Navigator by name to find assetKey."""
    url = f"https://msu.io/navigator/api/navigator/search?keyword={char_name}&limit=20"
    resp = await nav_client.get(url)
    if resp.status_code != 200:
        return None
    for rec in resp.json().get("records", []):
        if rec.get("type") == "character" and rec.get("character", {}).get("characterName", "").lower() == char_name.lower():
            return rec["character"]
    return None


# Set of permanently unenrichable token IDs (not in Navigator, bad URI, etc)
_unenrichable: Set[str] = set()

# ── Enrichment stats tracking ────────────────────────────────────────────
_enrich_ok = 0
_enrich_skip = 0
_enrich_errors = 0
_enrich_batch_count = 0

def get_enrich_stats() -> dict:
    """Return enrichment statistics for the /enrich-stats endpoint."""
    total = _enrich_ok + _enrich_skip + _enrich_errors
    rate = (_enrich_ok / total * 100) if total > 0 else 0
    return {
        "total_ok": _enrich_ok,
        "total_skipped": _enrich_skip,
        "total_errors": _enrich_errors,
        "success_rate": f"{rate:.1f}%",
        "batches_processed": _enrich_batch_count,
        "unenrichable_count": len(_unenrichable),
    }


async def _populate_from_navigator(token_id: str, settings, nav_client: httpx.AsyncClient) -> bool:
    """
    Pipeline: tokenURI → name → search → assetKey → detail
    CP comes from apStat.attackPower in the Navigator response.
    """
    max_retries = 3
    backoffs = [2, 5, 15]
    prefix = f"[Populate-{token_id}]"
    token_id = "".join(c for c in token_id if c.isprintable()).strip()

    for attempt in range(max_retries):
        try:
            # Step 1: Get name
            char_name = await _token_uri_metadata(token_id)
            if not char_name:
                print(f"  {prefix} No name from tokenURI")
                return False

            # Step 2: Search assetKey
            char_info = await _search_asset_key(char_name, nav_client)
            if not char_info:
                print(f"  {prefix} Name '{char_name}' not found")
                return False

            asset_key = char_info.get("assetKey", "")
            if not asset_key:
                print(f"  {prefix} No assetKey for '{char_name}'")
                return False

            # Step 3: Detail
            url = f"https://msu.io/navigator/api/navigator/characters/{asset_key}/info"
            headers = {
                **NAV_HEADERS,
                "referer": f"https://msu.io/navigator/character/{asset_key}",
            }
            resp = await nav_client.get(url, headers=headers)

            if resp.status_code == 429:
                await asyncio.sleep(backoffs[min(attempt, len(backoffs)-1)])
                continue
            if resp.status_code != 200:
                print(f"  {prefix} HTTP {resp.status_code}")
                return False

            char_data = resp.json().get("character", {})
            if not char_data:
                print(f"  {prefix} No character data in response")
                return False

            common = char_data.get("common", {})
            job_info = common.get("job", {})

            name = common.get("name", char_data.get("name", ""))
            if not name:
                return False

            job_name = job_info.get("jobName", "")
            class_name = job_info.get("className", "")
            class_code = job_info.get("classCode", 0)
            job_code = job_info.get("jobCode", 0)
            level = common.get("level", 0)
            image_url = char_data.get("imageUrl", "")
            asset_key_resp = char_data.get("assetKey", "")

            # CP — from apStat.attackPower (string like "7022811") or fallback to pad/mad total
            ap_stat = char_data.get("apStat") or {}
            cp_val = 0

            if ap_stat:
                cp_raw = ap_stat.get("attackPower", 0)
                try:
                    cp_val = int(cp_raw) if cp_raw else 0
                except (ValueError, TypeError):
                    cp_val = 0

                # Fallback: pad.total / mad.total (nested {total, base, enhance} format)
                if cp_val == 0:
                    pad_obj = ap_stat.get("pad", {})
                    mad_obj = ap_stat.get("mad", {})
                    pad_total = int(pad_obj.get("total", 0) or 0) if isinstance(pad_obj, dict) else int(pad_obj or 0)
                    mad_total = int(mad_obj.get("total", 0) or 0) if isinstance(mad_obj, dict) else int(mad_obj or 0)
                    keys_sample = list(ap_stat.keys())[:8]
                    print(f"  {prefix} FALLBACK — attackPower=0, keys={keys_sample}, pad_total={pad_total}, mad_total={mad_total}")
                    if pad_total > 0 or mad_total > 0:
                        cp_val = max(pad_total, mad_total)

            if cp_val == 0:
                ap_keys = list(ap_stat.keys())[:10] if ap_stat else "EMPTY"
                print(f"  {prefix} SKIP — CP=0, assetKey={asset_key}, apStat keys: {ap_keys}")
                _unenrichable.add(token_id)
                return False

            hyper_stat = char_data.get("hyperStat", {})
            wearing = char_data.get("wearing", {})

            print(f"  {prefix} CP={cp_val:>10} | {name} | Lv{level} | {job_name}")

            from db.database import CharacterSnapshot, MintEvent, async_session

            async with async_session() as session:
                existing = (await session.execute(
                    select(CharacterSnapshot).where(CharacterSnapshot.token_id == token_id)
                )).scalar_one_or_none()

                snapshot_data = {
                    "token_id": token_id,
                    "asset_key": asset_key_resp,
                    "name": name,
                    "class_name": class_name,
                    "job_name": job_name,
                    "class_code": class_code,
                    "job_code": job_code,
                    "level": level,
                    "combat_power": cp_val,
                    "char_att": _get_stat_total(ap_stat, "pad"),
                    "char_matt": _get_stat_total(ap_stat, "mad"),
                    "ap_stats_json": json.dumps(ap_stat, ensure_ascii=False) if ap_stat else None,
                    "hyper_stats_json": json.dumps(hyper_stat, ensure_ascii=False) if hyper_stat else None,
                    "wearing_json": json.dumps(wearing, ensure_ascii=False) if wearing else None,
                    "equipped_items_json": None,
                    "image_url": image_url,
                    "price_wei": "0",
                    "source": "navigator",
                }

                if existing:
                    for k, v in snapshot_data.items():
                        if k != "token_id":
                            setattr(existing, k, v)
                else:
                    session.add(CharacterSnapshot(**snapshot_data))
                await session.commit()

                evt = (await session.execute(
                    select(MintEvent).where(MintEvent.token_id == token_id)
                )).scalar_one_or_none()
                if evt and not evt.enriched:
                    evt.enriched = True
                    evt.retry_count = 0
                    await session.commit()

            return True

        except Exception as e:
            print(f"  [Populate RETRY {attempt+1}/{max_retries}] {token_id}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(backoffs[attempt])
            else:
                print(f"  [Populate ERR] {token_id} after {max_retries} retries")
                # Mark max retries so we don't keep retrying
                _unenrichable.add(token_id)
                try:
                    async with async_session() as session:
                        from db.database import MintEvent
                        evt = (await session.execute(
                            select(MintEvent).where(MintEvent.token_id == token_id)
                        )).scalar_one_or_none()
                        if evt:
                            evt.retry_count = max_retries
                            await session.commit()
                except Exception:
                    pass

    return False


async def run_populate(nft_type: str, batch_size: int = 10):
    """Continuous enrichment — shared httpx client, high concurrency.

    Only processes tokens that have no snapshot at all OR have CP > 0.
    Characters without CP data are skipped and never retried.
    """
    await _ensure_db_tables()

    from db.database import NftMintLookup, async_session, CharacterSnapshot
    from config import get_settings
    from services.proxy_pool import proxy_pool
    proxy_pool.load()

    settings = get_settings()
    if nft_type != "character":
        return

    prefix = f"[Populate-{nft_type}]"
    print(f"{prefix} Starting (batch_size={batch_size})...")

    async with httpx.AsyncClient(timeout=30.0, verify=False) as nav_client:
        # Cleanup: remove CP=0 dummy snapshots and reset their enriched flags
        from sqlalchemy import text
        try:
            async with async_session() as session:
                from db.database import CharacterSnapshot
                zero_cp = (await session.execute(
                    select(CharacterSnapshot.token_id).where(CharacterSnapshot.combat_power == 0)
                )).scalars().all()
                if zero_cp:
                    await session.execute(text("DELETE FROM character_snapshots WHERE combat_power = 0"))
                    await session.commit()
                    await session.execute(text("UPDATE mint_events SET enriched = false, retry_count = 0"))
                    await session.commit()
                    print(f"[Populate] Cleaned up {len(zero_cp)} CP=0 dummy snapshots, reset enriched flags")
        except Exception as e:
            print(f"[Populate] Cleanup warning: {e}")

        while True:
            try:
                # Get all minted tokens
                async with async_session() as session:
                    mint_q = select(NftMintLookup.token_id).where(NftMintLookup.nft_type == nft_type)
                    all_tokens: Set[str] = set((r[0] for r in (await session.execute(mint_q)).all()))

                    # Tokens that already have a snapshot with CP > 0
                    snapshot_q = select(CharacterSnapshot.token_id).where(CharacterSnapshot.combat_power > 0)
                    have_snapshot: Set[str] = set((r[0] for r in (await session.execute(snapshot_q)).all()))

                # Skip: already enriched (CP > 0) or permanently unenrichable
                pending = all_tokens - have_snapshot - _unenrichable

                if not pending:
                    await asyncio.sleep(30)
                    continue

                print(f"{prefix} {len(pending)} new characters to enrich...")

                sem = asyncio.Semaphore(10)

                async def populate_one(tid: str):
                    async with sem:
                        return await _populate_from_navigator(tid, settings, nav_client)

                batch = list(pending)[:batch_size]
                results = await asyncio.gather(*[populate_one(tid) for tid in batch], return_exceptions=True)

                global _enrich_ok, _enrich_skip, _enrich_errors, _enrich_batch_count
                ok = sum(1 for r in results if r is True)
                skipped = sum(1 for r in results if r is False)
                errs = sum(1 for r in results if isinstance(r, Exception))
                _enrich_ok += ok
                _enrich_skip += skipped
                _enrich_errors += errs
                _enrich_batch_count += 1
                done = ok + skipped  # False means permanently unenrichable, add to skip set

                print(f"{prefix} Batch: {ok} enriched, {skipped} skipped, {errs} errors")

                if _enrich_batch_count % 10 == 0:
                    total_runs = _enrich_ok + _enrich_skip + _enrich_errors
                    rate = (_enrich_ok / total_runs * 100) if total_runs > 0 else 0
                    print(f"[Populate] Stats: {_enrich_ok} ok, {_enrich_skip} skipped, "
                          f"{_enrich_errors} errors ({rate:.1f}% success) | "
                          f"{_enrich_batch_count} batches")

                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"{prefix} Error: {e}")
                await asyncio.sleep(30)


# ── 4. PUBLIC API for main.py ──────────────────────────────────────────────

async def scan_all_task(limit_pages: int = 0):
    await run_full_scan("all", limit_pages=limit_pages)


async def enrich_chars_task(batch_size: int = 10):
    await run_populate("character", batch_size=batch_size)


async def enrich_items_task(batch_size: int = 30):
    prefix = "[Enrich-items]"
    print(f"{prefix} Not yet implemented")
    while True:
        await asyncio.sleep(60)


async def watch_chars_task():
    await run_mint_watcher("character")


async def watch_items_task():
    await run_mint_watcher("item")


# ── Re-enrich top characters periodically ─────────────────────────────────

async def re_enrich_task(interval_hours: int = 24):
    """Periodically re-enrich top 50 characters to keep CP current."""
    await _ensure_db_tables()
    prefix = "[Re-enrich]"
    from db.database import CharacterSnapshot, async_session

    print(f"{prefix} Starting (interval={interval_hours}h)")

    while True:
        try:
            async with async_session() as session:
                rows = (await session.execute(
                    select(CharacterSnapshot.token_id)
                    .where(CharacterSnapshot.combat_power > 0)
                    .order_by(CharacterSnapshot.combat_power.desc())
                    .limit(50)
                )).scalars().all()

            if not rows:
                await asyncio.sleep(60 * 10)
                continue

            print(f"{prefix} Refreshing top {len(rows)} characters...")
            from config import get_settings
            settings = get_settings()
            async with httpx.AsyncClient(timeout=30.0, verify=False) as nav_client:

                sem = asyncio.Semaphore(10)
                async def refresh_one(tid: str):
                    async with sem:
                        return await _populate_from_navigator(tid, settings, nav_client)

                results = await asyncio.gather(*[refresh_one(tid) for tid in rows], return_exceptions=True)
                ok = sum(1 for r in results if r is True)
                print(f"{prefix} Done: {ok}/{len(rows)} updated")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"{prefix} Error: {e}")

        await asyncio.sleep(interval_hours * 3600)
