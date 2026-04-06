"""
scan_all_items.py — Historic scan of ALL minted Item NFTs.

Same pattern as scan_all_characters.py but targets ITEM_NFT contract.

Usage:
    python scripts/scan_all_items.py
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
from db.database import NftMintLookup, MintEvent, SyncState, async_session, engine, Base
from config import get_settings

settings = get_settings()

# ── Constants ─────────────────────────────────────────────────────
ITEM_NFT = settings.ITEM_NFT.lower()
BASE_URL = "https://api.routescan.io/v2/network/mainnet/evm/68414"
PAGE_LIMIT = 100
CHECKPOINT_EVERY = 50
SLEEP_BETWEEN = 0.3


async def save_cursor(cursor_url: str, page: int, total_found: int, last_block: int):
    async with async_session() as session:
        for key, val in [
            ("scan_items_cursor", cursor_url or ""),
            ("scan_items_page", str(page)),
            ("scan_items_found", str(total_found)),
            ("scan_items_last_block", str(last_block)),
        ]:
            row = (await session.execute(select(SyncState).where(SyncState.key == key))).scalar_one_or_none()
            if row:
                row.value = val
            else:
                session.add(SyncState(key=key, value=val))
        await session.commit()


async def upsert_mint(token_id: str, nft_type: str, minter: str, block_number: int, timestamp: int) -> bool:
    async with async_session() as session:
        existing = (await session.execute(
            select(NftMintLookup).where(NftMintLookup.token_id == token_id)
        )).scalar_one_or_none()
        is_new = existing is None

        if is_new:
            session.add(NftMintLookup(
                token_id=token_id, nft_type=nft_type, minter=minter, block_number=block_number
            ))
            session.add(MintEvent(
                token_id=token_id, nft_type=nft_type, minter=minter,
                block_number=block_number, timestamp=timestamp, enriched=False,
            ))
            await session.commit()
        else:
            existing.block_number = max(existing.block_number, block_number)
            session.add(MintEvent(
                token_id=token_id, nft_type=nft_type, minter=minter,
                block_number=block_number, timestamp=timestamp, enriched=False,
            ))
            await session.commit()

    return is_new


async def run():
    stop_flag = [False]

    def _sigint(sig, frame):
        print("\n\n[CTRL+C] Stopping...")
        stop_flag[0] = True

    signal.signal(signal.SIGINT, _sigint)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Resume state
    async with async_session() as session:
        cursor_row = (await session.execute(select(SyncState).where(SyncState.key == "scan_items_cursor"))).scalar_one_or_none()
        page_row = (await session.execute(select(SyncState).where(SyncState.key == "scan_items_page"))).scalar_one_or_none()

    cursor_url = cursor_row.value if cursor_row else ""
    start_page = int(page_row.value) if page_row else 0

    if cursor_url:
        url = cursor_url
        print(f"[RESUME] page ~{start_page:,}")
    else:
        url = f"{BASE_URL}/erc721-transfers?tokenAddress={settings.ITEM_NFT}&limit={PAGE_LIMIT}"
        print(f"[START] Scanning all Item NFT transfers...")

    t0 = time.time()
    page = start_page

    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        while url and not stop_flag[0]:
            page += 1

            try:
                resp = await client.get(url, timeout=15.0)

                if resp.status_code == 429:
                    print(f"\n[429] Rate limited — waiting 15s")
                    await asyncio.sleep(15)
                    page -= 1
                    continue

                if resp.status_code != 200:
                    print(f"\n[HTTP {resp.status_code}] Stopping.")
                    break

                data = resp.json()
                items = data.get("items", [])
                link = data.get("link", {})
                next_path = link.get("next") if isinstance(link, dict) else None

                if not items:
                    print(f"\nNo more items at page {page:,}. Done!")
                    break

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
                            from datetime import datetime
                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            ts = int(dt.timestamp())
                        except Exception:
                            pass

                    await upsert_mint(token_id, "item", from_addr, block, ts)

                elapsed = time.time() - t0
                rate = page / elapsed if elapsed > 0 else 0
                sys.stdout.write(f"\r  Page {page:>7,}  |  {rate:.2f} pg/s  ")
                sys.stdout.flush()

                next_url = f"https://api.routescan.io{next_path}" if next_path else ""
                await save_cursor(next_url, page, 0, block if items else 0)

                if page % CHECKPOINT_EVERY == 0:
                    print(f"\n  ✓ Checkpoint at page {page:,}")

                if not next_path:
                    print(f"\nReached end of pagination. Scan complete!")
                    break

                url = f"https://api.routescan.io{next_path}"
                await asyncio.sleep(SLEEP_BETWEEN)

            except asyncio.CancelledError:
                stop_flag[0] = True
                break
            except Exception as e:
                print(f"\n[ERR] page {page}: {e} — retry in 3s")
                await asyncio.sleep(3)

    async with async_session() as session:
        count = (await session.execute(
            select(func.count(NftMintLookup.id)).where(NftMintLookup.nft_type == "item")
        )).scalar() or 0
    print(f"\n\n{'='*65}")
    print(f"  DONE  |  Pages: {page:,}  |  Unique items: {count:,}")
    print(f"{'='*65}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
