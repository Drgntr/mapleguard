"""
watch_new_mints.py — Live monitoring for new Character NFT mints.

Polls the blockchain every POLL_INTERVAL seconds for Transfer events
from 0x0 address on the CHARACTER_NFT contract. When a new mint is
detected, it's inserted into the DB and optionally enriched immediately.

Usage:
    python scripts/watch_new_mints.py
    python scripts/watch_new_mints.py --no-enrich   # just track, don't call Open API
"""

import asyncio
import httpx
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from db.database import NftMintLookup, MintEvent, SyncState, async_session, engine, Base
from config import get_settings
from services.proxy_pool import proxy_pool

settings = get_settings()

# ── Config ────────────────────────────────────────────────────────
POLL_INTERVAL = 5
CHAR_NFT = settings.CHARACTER_NFT
RPC_URL = settings.RPC_URL
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ENRICH_ON_MINT = True  # Auto-enrich new mints via Open API


def _hex_to_address(hex_str: str) -> str:
    if not hex_str or hex_str == "0x":
        return ""
    return "0x" + hex_str[2:].lower().zfill(40)[-40:]


async def get_current_block(client: httpx.AsyncClient) -> int:
    try:
        r = await client.post(RPC_URL, json={
            "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1,
        })
        return int(r.json()["result"], 16)
    except Exception:
        return 0


async def get_block_timestamp(client: httpx.AsyncClient, block_num: int) -> int:
    try:
        r = await client.post(RPC_URL, json={
            "jsonrpc": "2.0",
            "method": "eth_getBlockByNumber",
            "params": [hex(block_num), False],
            "id": 1,
        })
        result = r.json().get("result")
        if result and result.get("timestamp"):
            return int(result["timestamp"], 16)
    except Exception:
        pass
    return int(time.time())


async def get_logs(client: httpx.AsyncClient, from_block: int, to_block: int) -> list:
    """Fetch Transfer events from CHAR_NFT in block range."""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{
            "address": CHAR_NFT,
            "topics": [TRANSFER_TOPIC, "0x" + "0" * 64],  # from=0x0 (mint)
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
        }],
        "id": 1,
    }
    try:
        r = await client.post(RPC_URL, json=payload, timeout=20.0)
        res = r.json()
        if "result" in res and isinstance(res["result"], list):
            return res["result"]
        return []
    except Exception:
        return []


async def process_mint(client: httpx.AsyncClient, log: dict, do_enrich: bool):
    """Process a single mint event: save to DB, optionally enrich."""
    topics = log.get("topics", [])
    if len(topics) != 4:
        return {
            "token_id": "",
            "minter": _hex_to_address(topics[2] if len(topics) > 2 else ""),
            "new": False,
        }

    token_id = str(int(topics[3], 16))
    minter = _hex_to_address(topics[2])
    block_num = int(log.get("blockNumber", "0x0"), 16)
    timestamp = await get_block_timestamp(client, block_num)

    # Check if already in DB
    async with async_session() as session:
        existing = (await session.execute(
            select(NftMintLookup.id).where(NftMintLookup.token_id == token_id)
        )).scalar_one_or_none()

        if not existing:
            session.add(NftMintLookup(
                token_id=token_id, nft_type="character", minter=minter,
                block_number=block_num,
            ))
            session.add(MintEvent(
                token_id=token_id, nft_type="character", minter=minter,
                block_number=block_num, timestamp=timestamp, enriched=False,
            ))
            await session.commit()

    if do_enrich and not existing:
        await enrich_new_mint(client, token_id)

    return {"token_id": token_id, "minter": minter, "new": existing is None}


async def enrich_new_mint(client: httpx.AsyncClient, token_id: str):
    from models.character import CharacterListing
    from services.combat_power_engine import CombatPowerEngine, _get_stat_total
    import json

    url = f"{settings.MSU_OPENAPI_BASE}/characters/by-token-id/{token_id}"
    headers = {
        "accept": "application/json",
        "x-nxopen-api-key": settings.MSU_OPENAPI_KEY,
    }
    proxy_url = proxy_pool.get_proxy()
    extra = {"proxy": proxy_url} if proxy_url else {}

    try:
        resp = await client.get(url, headers=headers, timeout=30, **extra)
        if resp.status_code != 200:
            print(f"  [Enrich] Failed for {token_id}: HTTP {resp.status_code}")
            return

        body = resp.json()
        if not body.get("success") or not body.get("data"):
            return

        char_data = body["data"]
        char_obj = CharacterListing.from_openapi(char_data.get("character", char_data))

        # Compute CP synchronously
        combat_power = 0
        char_att = 0.0
        char_matt = 0.0
        try:
            ap = char_data.get("apStat", {})
            cp_val = CombatPowerEngine.calculate_cp(
                primary_stat=_get_stat_total(ap, "str"),
                secondary_stat=_get_stat_total(ap, "dex"),
                total_att=max(_get_stat_total(ap, "pad"), _get_stat_total(ap, "attackPower"), _get_stat_total(ap, "mad")),
                damage_pct=_get_stat_total(ap, "damage"),
                boss_damage_pct=_get_stat_total(ap, "boss_monster_damage"),
                crit_damage_pct=_get_stat_total(ap, "critical_damage"),
                crit_damage_base=0.0,
            )
            combat_power = int(cp_val) if cp_val > 0 else 0
            char_att = _get_stat_total(ap, "pad")
            char_matt = _get_stat_total(ap, "mad")
        except Exception as e:
            print(f"  [CP error] {token_id}: {e}")

        from db.database import CharacterSnapshot

        ap_stats = json.dumps(char_obj.ap_stats.model_dump(), ensure_ascii=False) if char_obj.ap_stats else None

        async with async_session() as session:
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
                ap_stats_json=ap_stats,
                image_url=char_obj.image_url,
                source="openapi",
            ))

            # Update MintEvent enriched flag
            stmt = select(MintEvent).where(
                MintEvent.token_id == token_id,
                MintEvent.nft_type == "character",
                MintEvent.enriched == False,
            ).order_by(MintEvent.id.desc())
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row:
                row.enriched = True

            await session.commit()

        print(f"  [Enrich OK] {token_id} | {char_obj.name[:20]} | CP {combat_power:,}")

    except Exception as e:
        print(f"  [Enrich ERR] {token_id}: {e}")


async def run(no_enrich: bool = False):
    stop_flag = [False]

    def _sigint(sig, frame):
        print("\n[Stopping...]")
        stop_flag[0] = True

    signal.signal(signal.SIGINT, _sigint)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    proxy_pool.load()

    # Get last known block
    async with async_session() as session:
        row = (await session.execute(
            select(SyncState).where(SyncState.key == "watch_characters_last_block")
        )).scalar_one_or_none()
        last_block = int(row.value) if row and row.value.isdigit() else 0

    print(f"{'='*65}")
    print(f"  Character Mint Watcher — Live Monitor")
    print(f"  Last indexed block: {last_block:,}")
    print(f"  Poll interval: {POLL_INTERVAL}s")
    print(f"  Auto-enrich: {'YES' if not no_enrich else 'NO'}")
    print(f"{'='*65}\n")

    async with httpx.AsyncClient(timeout=20.0) as client:
        while not stop_flag[0]:
            try:
                head = await get_current_block(client)
                if head == 0:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                if head <= last_block:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                logs = await get_logs(client, last_block + 1, head)

                if logs:
                    for log in logs:
                        result = await process_mint(client, log, do_enrich=not no_enrich)
                        if result["new"]:
                            print(f"  [NEW MINT] {result['token_id']} | "
                                  f"minter: {result['minter'][:10]}... | "
                                  f"block {last_block + 1:,}")

                last_block = head

                # Save state
                async with async_session() as session:
                    row = (await session.execute(
                        select(SyncState).where(SyncState.key == "watch_characters_last_block")
                    )).scalar_one_or_none()
                    if row:
                        row.value = str(head)
                    else:
                        session.add(SyncState(key="watch_characters_last_block", value=str(head)))
                    await session.commit()

            except asyncio.CancelledError:
                stop_flag[0] = True
                break
            except Exception as e:
                print(f"\n[Watch error] {e}")
                await asyncio.sleep(10)

            await asyncio.sleep(POLL_INTERVAL)

    print("\nWatcher stopped.")


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--no-enrich", action="store_true", help="Don't auto-enrich new mints")
    args = parser.parse_args()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run(no_enrich=args.no_enrich))
