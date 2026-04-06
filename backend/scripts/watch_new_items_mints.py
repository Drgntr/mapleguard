"""
watch_new_items_mints.py — Live monitoring for new Item NFT mints.

Same pattern as watch_new_mints.py but for ITEM_NFT contract.

Usage:
    python scripts/watch_new_items_mints.py
    python scripts/watch_new_items_mints.py --no-enrich
"""

import asyncio
import httpx
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from db.database import NftMintLookup, MintEvent, SyncState, async_session, engine, Base
from config import get_settings
from services.proxy_pool import proxy_pool

settings = get_settings()

# ── Config ────────────────────────────────────────────────────────
POLL_INTERVAL = 5
ITEM_NFT = settings.ITEM_NFT
RPC_URL = settings.RPC_URL
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


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
            "jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": [hex(block_num), False], "id": 1,
        })
        result = r.json().get("result")
        if result and result.get("timestamp"):
            return int(result["timestamp"], 16)
    except Exception:
        pass
    return int(time.time())


async def get_logs(client: httpx.AsyncClient, from_block: int, to_block: int) -> list:
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{
            "address": ITEM_NFT,
            "topics": [TRANSFER_TOPIC, "0x" + "0" * 64],
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
    topics = log.get("topics", [])
    if len(topics) != 4:
        return {"token_id": "", "minter": "", "new": False}

    token_id = str(int(topics[3], 16))
    minter = _hex_to_address(topics[2])
    block_num = int(log.get("blockNumber", "0x0"), 16)
    timestamp = await get_block_timestamp(client, block_num)

    async with async_session() as session:
        existing = (await session.execute(
            select(NftMintLookup.id).where(NftMintLookup.token_id == token_id)
        )).scalar_one_or_none()

        if not existing:
            session.add(NftMintLookup(
                token_id=token_id, nft_type="item", minter=minter,
                block_number=block_num,
            ))
            session.add(MintEvent(
                token_id=token_id, nft_type="item", minter=minter,
                block_number=block_num, timestamp=timestamp, enriched=False,
            ))
            await session.commit()

    if do_enrich and not existing:
        await enrich_new_mint(client, token_id)

    return {"token_id": token_id, "minter": minter, "new": existing is None}


async def enrich_new_mint(client: httpx.AsyncClient, token_id: str):
    try:
        url = f"{settings.MSU_OPENAPI_BASE}/items/by-token-id/{token_id}"
        headers = {"accept": "application/json", "x-nxopen-api-key": settings.MSU_OPENAPI_KEY}
        proxy_url = proxy_pool.get_proxy()
        extra = {"proxy": proxy_url} if proxy_url else {}

        resp = await client.get(url, headers=headers, timeout=30, **extra)
        if resp.status_code != 200:
            print(f"  [Item Enrich] Failed for {token_id}: HTTP {resp.status_code}")
            return

        body = resp.json()
        if not body.get("success") or not body.get("data"):
            return

        item_data = body["data"].get("item", body["data"])
        from models.item import ItemListing
        item_obj = ItemListing.from_openapi(item_data)

        import json
        enh = item_data.get("enhance", {})
        starforce = enh.get("starforce", {}).get("enhanced", 0) or 0
        stats = json.dumps(item_obj.stats.model_dump(), ensure_ascii=False) if item_obj.stats else None

        from db.database import ItemSnapshot
        async with async_session() as session:
            session.add(ItemSnapshot(
                token_id=token_id,
                asset_key=item_data.get("assetKey"),
                name=item_obj.name or "",
                category_no=item_obj.category_no,
                category_label=item_obj.category_label,
                item_id=item_obj.item_id,
                starforce=starforce,
                enable_starforce=item_obj.enable_starforce,
                potential_grade=item_obj.potential_grade,
                bonus_potential_grade=item_obj.bonus_potential_grade,
                stats_json=stats,
                image_url=item_obj.image_url,
                source="openapi",
            ))

            stmt = select(MintEvent).where(
                MintEvent.token_id == token_id,
                MintEvent.nft_type == "item",
                MintEvent.enriched == False,
            ).order_by(MintEvent.id.desc())
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row:
                row.enriched = True

            await session.commit()

        print(f"  [Item Enrich OK] {token_id} | {item_obj.name[:30]}")

    except Exception as e:
        print(f"  [Item Enrich ERR] {token_id}: {e}")


async def run(no_enrich: bool = False):
    stop_flag = [False]

    def _sigint(sig, frame):
        print("\n[Stopping...]")
        stop_flag[0] = True

    signal.signal(signal.SIGINT, _sigint)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    proxy_pool.load()

    async with async_session() as session:
        row = (await session.execute(
            select(SyncState).where(SyncState.key == "watch_items_last_block")
        )).scalar_one_or_none()
        last_block = int(row.value) if row and row.value.isdigit() else 0

    print(f"{'='*65}")
    print(f"  Item Mint Watcher — Live Monitor")
    print(f"  Last indexed block: {last_block:,}")
    print(f"  Poll interval: {POLL_INTERVAL}s")
    print(f"  Auto-enrich: {'YES' if not no_enrich else 'NO'}")
    print(f"{'='*65}\n")

    async with httpx.AsyncClient(timeout=20.0) as client:
        while not stop_flag[0]:
            try:
                head = await get_current_block(client)
                if head == 0 or head <= last_block:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                logs = await get_logs(client, last_block + 1, head)

                if logs:
                    for log in logs:
                        result = await process_mint(client, log, do_enrich=not no_enrich)
                        if result["new"]:
                            print(f"  [NEW ITEM] {result['token_id']} | "
                                  f"minter: {result['minter'][:10]}...")

                last_block = head

                async with async_session() as session:
                    row = (await session.execute(
                        select(SyncState).where(SyncState.key == "watch_items_last_block")
                    )).scalar_one_or_none()
                    if row:
                        row.value = str(head)
                    else:
                        session.add(SyncState(key="watch_items_last_block", value=str(head)))
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
