"""
Blockchain Indexer — Python-native, no Docker/Redis required.

Monitors 3 contracts on Henesys (chain 68414):
  • Payment Token (NESO ERC-20): 0x07E49Ad54FcD23F6e7B911C2068F0148d1827c08
  • Item NFT (ERC-721):           0x43DCff2A0cedcd5e10e6f1c18b503498dDCe60d5
  • Character NFT (ERC-721):      0xcE8e48Fae05c093a4A1a1F569BDB53313D765937
  • Marketplace:                  0x6813869c3e5dec06e6f88b42d41487dc5d7abf57

Events captured:
  • ERC-721 Transfer(from, to, tokenId) → mints, transfers, sales
  • OrderCreated(maker, tokenId, price, listingTime) → who listed what
  • OrderMatched(orderId, nftAddr, seller, buyer, tokenId, price, timestamp) → who bought from whom

All data persisted to SQLite + in-memory whale tracker stats.
Runs continuously with catch-up → live mode.
"""

import asyncio
import concurrent.futures
import json
import os
import time
import httpx
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from config import get_settings
from db.database import async_session, init_db

settings = get_settings()

# ── Contract addresses ────────────────────────────────────────────────
MARKETPLACE = settings.MARKETPLACE_CONTRACT.lower()
CHAR_NFT = settings.CHARACTER_NFT.lower()
ITEM_NFT = settings.ITEM_NFT.lower()

RPC_URL = settings.RPC_URL

# ── Event signatures (topic0) — Henesys custom marketplace ────────────
# Exchange721Matched(bytes32 orderId, bytes32 nftId, address seller, address buyer, uint256 price)
EXCHANGE721_MATCHED = "0x17daabe2b1972bd6ae2a9aad2b92f547aa11fd7039890fdf3dae6b0da37b048c"
# Exchange1155Matched(bytes32, bytes32, address, address, uint256 tokenId, uint256 amount)
EXCHANGE1155_MATCHED = "0x6dad30daaa71a829d007bd18bc5c868bdc2789537da19f02880cd2b4dc824a96"
# SendCommission (commission event — informational only)
COMMISSION_EVENT = "0x973156da8202e6c114c3570e2feb2e8f3f90d130a6c3eae00005ddf7b0420fbc"
# ERC-721 Transfer(address,address,uint256)
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# ── State paths ───────────────────────────────────────────────────────
STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
STATE_FILE = os.path.join(STATE_DIR, "indexer_state.json")

# ── Scan config ───────────────────────────────────────────────────────
BATCH_SIZE = 5000          # blocks per eth_getLogs request
CATCHUP_BATCH = 50_000     # blocks per pass during backlog catch-up
POLL_INTERVAL = 5          # seconds between checks in live mode
NESO_DECIMALS = 18


class BlockchainIndexer:
    def __init__(self):
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None
        self._last_block = 0
        self._start_block = 0
        self._head_block = 0
        self._events_total = 0
        self._catching_up = False

        # In-memory rolling stats (reset on scan_once, accumulated over time)
        self._order_matched: list[dict] = []   # {seller, buyer, token_id, price, ts, nft_type}
        self._transfers: list[dict] = []       # {from_addr, to_addr, token_id, ts, nft_type}

        # Cumulative stats (never reset, for whale tracker)
        self._cumulative_spenders: dict = {}
        self._cumulative_earners: dict = {}
        self._cumulative_mints: dict = {}
        self._all_matched: dict = {}           # tx_hash -> match record
        self._all_transfers: dict = []         # full transfer log

        # Block batch of processed txs (dedup)
        self._seen_tx: set = set()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                self._last_block = state.get("last_block", 0)
                self._start_block = state.get("start_block", 0)
                self._seen_tx = set(state.get("processed_txs", []))
                # Restore cumulative data
                self._cumulative_spenders = state.get("cumulative_spenders", {})
                self._cumulative_earners = state.get("cumulative_earners", {})
                self._cumulative_mints = state.get("cumulative_mints", {})
                self._all_matched = state.get("all_matched", {})
                self._all_transfers = state.get("all_transfers", [])
                self._events_total = state.get("events_total", 0)
                print(f"[Indexer] Resumed: last_block={self._last_block}, "
                      f"events={self._events_total}, matched={len(self._all_matched)}, "
                      f"transfers={len(self._all_transfers)}")
            except Exception as e:
                print(f"[Indexer] State load error: {e}")

    def _save_state(self, full: bool = False):
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            state = {
                "last_block": self._last_block,
                "start_block": self._start_block,
                "events_total": self._events_total,
                "processed_txs": list(self._seen_tx) if full else [],
                "cumulative_spenders": self._cumulative_spenders,
                "cumulative_earners": self._cumulative_earners,
                "cumulative_mints": self._cumulative_mints,
                "all_matched": dict(list(self._all_matched.items())[-20000:]),  # cap at 20k
                "all_transfers": self._all_transfers[-50000:],                  # cap at 50k
            }
            with open(STATE_FILE, "w") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"[Indexer] State save error: {e}")

    def _rpc_sync(self, method: str, params: list = None) -> dict:
        import httpx
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1,
        }
        with httpx.Client(timeout=60.0) as client:
            r = client.post(RPC_URL, json=payload, headers={"Content-Type": "application/json"})
            return r.json()

    async def _rpc(self, method: str, params: list = None, retries: int = 2) -> dict:
        for attempt in range(retries):
            try:
                result = await asyncio.to_thread(self._rpc_sync, method, params)
                return result
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                else:
                    print(f"[Indexer] RPC error {method}: {e}")
                    return {}

    async def get_current_block(self) -> int:
        r = await self._rpc("eth_blockNumber")
        if "result" in r:
            return int(r["result"], 16)
        return 0

    async def get_block_timestamp(self, block_num: int) -> int:
        r = await self._rpc("eth_getBlockByNumber", [hex(block_num), False])
        if "result" in r and r["result"] and r["result"].get("timestamp"):
            return int(r["result"]["timestamp"], 16)
        return int(time.time())

    # ── Log fetching ──────────────────────────────────────────────────

    async def _get_logs(self, from_block: int, to_block: int,
                        topics: list[str] | None = None,
                        address: str | list[str] | None = None) -> list[dict]:
        filter_obj = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
        }
        if topics:
            filter_obj["topics"] = topics
        if address:
            filter_obj["address"] = address if isinstance(address, list) else [address]

        r = await self._rpc("eth_getLogs", [filter_obj])
        if "result" in r and isinstance(r["result"], list):
            return r["result"]
        if "error" in r:
            print(f"[Indexer] getLogs error: {r['error'].get('message', r['error'])}")
        return []

    # ── Event processing ──────────────────────────────────────────────

    def _hex_to_address(self, hex_str: str) -> str:
        if not hex_str or hex_str == "0x":
            return ""
        return ("0x" + hex_str[2:].lower().zfill(40))[-42:]

    def _process_transfer_log(self, log: dict, timestamp: int):
        """ERC-721 Transfer(address,address,uint256) — 4 topics."""
        topics = log.get("topics", [])
        if len(topics) != 4:
            return  # Not ERC-721 (ERC-20 has 3 topics)

        from_addr = self._hex_to_address(topics[1])
        to_addr = self._hex_to_address(topics[2])
        token_id = str(int(topics[3], 16))
        contract = log.get("address", "").lower()
        tx_hash = log.get("transactionHash", "")
        is_mint = from_addr == "0x0000000000000000000000000000000000000000"

        nft_type = "character" if contract == CHAR_NFT else "item" if contract == ITEM_NFT else "unknown"
        if nft_type == "unknown":
            return

        record = {
            "tx_hash": tx_hash,
            "from_addr": from_addr,
            "to_addr": to_addr,
            "token_id": token_id,
            "contract": contract,
            "nft_type": nft_type,
            "timestamp": timestamp,
            "block_num": log.get("blockNumber", ""),
            "is_mint": is_mint,
        }

        self._transfers.append(record)
        self._all_transfers.append(record)

        # Track mints
        if is_mint:
            self._cumulative_mints[to_addr] = self._cumulative_mints.get(to_addr, 0) + 1

    def _process_exchange721_matched(self, log: dict, timestamp: int):
        """Exchange721Matched(bytes32 orderId, bytes32 nftId, address seller, address buyer, uint256 price)
        topics[1] = seller, topics[2] = buyer
        data = orderId(32) + nftId(32) + price(32) = 96 bytes = 3 words
        """
        topics = log.get("topics", [])
        data = log.get("data", "")[2:]
        if len(data) < 96:
            return

        tx_hash = log.get("transactionHash", "")
        seller = self._hex_to_address(topics[1]) if len(topics) > 1 else ""
        buyer = self._hex_to_address(topics[2]) if len(topics) > 2 else ""

        order_id = data[0:64]
        nft_id = data[64:128]
        price_wei = int(data[128:192], 16)
        price = price_wei / (10 ** NESO_DECIMALS)

        # Determine NFT type by checking if nft_id matches a Character NFT token_id
        # We'll check against known Character NFT transfers later; for now use heuristics
        # Characters have smaller token_ids than Items
        token_id_str = str(int(nft_id, 16))

        # Cross-reference with the Transfer event in same tx
        nft_type = "unknown"
        nft_addr = ""
        for t in self._transfers[-500:]:
            if t.get("seller_block") == log.get("blockNumber"):
                # Match by same block and transfer between same parties
                if t.get("from_addr") == seller and t.get("to_addr") == buyer:
                    nft_type = t.get("nft_type", "unknown")
                    nft_addr = t.get("contract", "")
                    break

        # If still unknown, try to resolve via the Transfer event in same block
        if nft_type == "unknown":
            bn = log.get("blockNumber", "")
            for t in self._transfers[-500:]:
                if t.get("block_num") == bn:
                    nft_type = t.get("nft_type", "unknown")
                    nft_addr = t.get("contract", "")
                    break

        # Fallback: assume character if not matched
        if nft_type == "unknown":
            # Most trades in early blocks are characters
            nft_type = "character"
            nft_addr = CHAR_NFT

        # Match by block_num to find NFT type
        bn = log.get("blockNumber", "")
        if nft_type == "unknown":
            for t in self._transfers[-500:]:
                if t.get("block_num") == bn and (
                    (t.get("from_addr") == seller and t.get("to_addr") == buyer)
                    or (t.get("from_addr") == seller)
                ):
                    nft_type = t.get("nft_type", "unknown")
                    nft_addr = t.get("contract", "")
                    break

        record = {
            "tx_hash": tx_hash,
            "seller": seller,
            "buyer": buyer,
            "order_id": "0x" + order_id,
            "nft_id": "0x" + nft_id,
            "nft_addr": nft_addr,
            "token_id": token_id_str,
            "price": price,
            "price_wei": str(price_wei),
            "nft_type": nft_type,
            "timestamp": timestamp,
            "listing_time": None,
            "time_to_purchase_sec": None,
            "instant_buy": False,
            "block_num": bn,
        }

        self._order_matched.append(record)
        self._all_matched[tx_hash] = record

        # Cumulative buyer spending
        if buyer:
            self._cumulative_spenders[buyer] = round(
                self._cumulative_spenders.get(buyer, 0) + price, 2
            )

        # Cumulative seller earnings
        if seller and not seller.startswith("0x0000"):
            self._cumulative_earners[seller] = round(
                self._cumulative_earners.get(seller, 0) + price, 2
            )

        self._events_total += 1

    def _process_exchange1155_matched(self, log: dict, timestamp: int):
        """Exchange1155Matched(bytes32, bytes32, address, address, uint256 tokenId, uint256 amount)
        topics[1] = seller, topics[2] = buyer, topics[3] = typeId
        data[0:64] = ?, data[64:128] = ?, data[128:192] = tokenId, data[192:256] = amount
        """
        topics = log.get("topics", [])
        data = log.get("data", "")[2:]
        if len(data) < 192:
            return

        tx_hash = log.get("transactionHash", "")
        seller = self._hex_to_address(topics[1]) if len(topics) > 1 else ""
        buyer = self._hex_to_address(topics[2]) if len(topics) > 2 else ""

        # For 1155, item types are items not characters
        token_id_val = int(data[128:192], 16)
        price_wei = int(data[192:256], 16) if len(data) >= 256 else 0
        price = price_wei / (10 ** NESO_DECIMALS)

        record = {
            "tx_hash": tx_hash,
            "seller": seller,
            "buyer": buyer,
            "nft_addr": ITEM_NFT,
            "token_id": str(token_id_val),
            "price": price,
            "price_wei": str(price_wei),
            "nft_type": "item",
            "timestamp": timestamp,
            "listing_time": None,
            "time_to_purchase_sec": None,
            "instant_buy": False,
        }

        self._order_matched.append(record)
        self._all_matched[tx_hash] = record

        if buyer:
            self._cumulative_spenders[buyer] = round(
                self._cumulative_spenders.get(buyer, 0) + price, 2
            )
        if seller and not seller.startswith("0x0000"):
            self._cumulative_earners[seller] = round(
                self._cumulative_earners.get(seller, 0) + price, 2
            )

        self._events_total += 1
        print(f"[Indexer] 1155 trade: tokenId={token_id_val} @ {price:,.0f} NESO | "
              f"seller={seller[:10]}... buyer={buyer[:10]}...")

    # ── Block processing ──────────────────────────────────────────────

    async def _process_block_range(self, from_block: int, to_block: int,
                                    cache_timestamps: dict) -> int:
        events_count = 0

        # Fetch logs in parallel
        matched_logs_future = self._get_logs(
            from_block, to_block,
            topics=[EXCHANGE721_MATCHED],
            address=[MARKETPLACE]
        )
        matched1155_future = self._get_logs(
            from_block, to_block,
            topics=[EXCHANGE1155_MATCHED],
            address=[MARKETPLACE]
        )
        char_transfers_future = self._get_logs(
            from_block, to_block,
            topics=[TRANSFER_TOPIC],
            address=[CHAR_NFT]
        )
        item_transfers_future = self._get_logs(
            from_block, to_block,
            topics=[TRANSFER_TOPIC],
            address=[ITEM_NFT]
        )

        matched_logs, matched1155, char_transfers, item_transfers = await asyncio.gather(
            matched_logs_future, matched1155_future, char_transfers_future, item_transfers_future,
            return_exceptions=True,
        )

        # Handle exceptions
        if isinstance(matched_logs, Exception):
            matched_logs = []
        if isinstance(matched1155, Exception):
            matched1155 = []
        if isinstance(char_transfers, Exception):
            char_transfers = []
        if isinstance(item_transfers, Exception):
            item_transfers = []

        # Cache timestamps for blocks we encounter
        blocks_to_fetch = set()
        all_items = list(matched_logs) + list(matched1155) + list(char_transfers) + list(item_transfers)
        for log in all_items:
            bn = log.get("blockNumber")
            if bn and int(bn, 16) not in cache_timestamps:
                blocks_to_fetch.add(int(bn, 16))

        # Batch fetch timestamps
        for block_num in blocks_to_fetch:
            cache_timestamps[block_num] = await self.get_block_timestamp(block_num)

        def ts(log):
            return cache_timestamps.get(int(log.get("blockNumber", "0x0"), 16), int(time.time()))

        # Process marketplace matched events
        for log in matched_logs:
            self._process_exchange721_matched(log, ts(log))
            events_count += 1

        for log in matched1155:
            self._process_exchange1155_matched(log, ts(log))
            events_count += 1

        # Process NFT transfers
        for log in char_transfers + item_transfers:
            self._process_transfer_log(log, ts(log))
            events_count += 1

        return events_count

    # ── Main loops ────────────────────────────────────────────────────

    async def _do_catchup(self, start_block: int, head: int):
        """Full historical index from start_block to current head."""
        self._catching_up = True
        print(f"[Indexer] CATCH-UP: {start_block} -> {head} ({head - start_block:,} blocks)")

        current = start_block
        while current < head and self._running:
            end = min(current + CATCHUP_BATCH, head)
            try:
                events = await self._process_block_range(current, end - 1, {})
                self._last_block = end
                log_freq = 50_000
                if current % log_freq >= end or events > 0:
                    print(f"[Indexer] Catch-up: block {end:,}/{head:,} | "
                          f"match={len(self._order_matched)}, "
                          f"transfers={len(self._transfers)}")
                current = end

                # Save periodically
                if self._events_total % 10000 < CATCHUP_BATCH * 3:
                    self._order_matched.clear()
                    self._transfers.clear()
                    self._seen_tx.clear()
                    self._save_state(full=False)

            except Exception as e:
                print(f"[Indexer] Catch-up error: {e}")
                await asyncio.sleep(10)

        self._catching_up = False
        print(f"[Indexer] Catch-up COMPLETE. Total events: {self._events_total:,}")
        self._save_state(full=True)

    async def _do_live_poll(self):
        """Live mode: poll for new blocks every POLL_INTERVAL seconds."""
        print(f"[Indexer] LIVE MODE (poll={POLL_INTERVAL}s)")
        poll_count = 0

        while self._running:
            try:
                head = await self.get_current_block()
                if head <= self._last_block:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                events = await self._process_block_range(
                    self._last_block + 1, head, {}
                )
                self._last_block = head
                poll_count += 1

                # Clear batch memory periodically
                self._order_matched.clear()
                self._transfers.clear()

                # Save every 10 polls or if events found
                if poll_count % 10 == 0 or events > 0:
                    self._seen_tx.clear()
                    self._save_state(full=(poll_count % 50 == 0))

                if poll_count % 10 == 0:
                    print(f"[Indexer] Live: block {self._last_block:,} | "
                          f"spenders={len(self._cumulative_spenders)}, "
                          f"earners={len(self._cumulative_earners)}, "
                          f"matched={len(self._all_matched):,}, "
                          f"transfers={len(self._all_transfers):,}")

            except Exception as e:
                print(f"[Indexer] Live poll error: {e}")
                await asyncio.sleep(30)

            await asyncio.sleep(POLL_INTERVAL)

    async def scan_once(self):
        """Run a single scan pass (useful for manual triggers)."""
        head = await self.get_current_block()
        if head == 0:
            print("[Indexer] Could not reach chain")
            return
        self._head_block = head
        if self._start_block == 0:
            self._start_block = 1  # Start from block 1 (genesis has no events)
        print(f"[Indexer] scan_once: {self._last_block} -> {head}")
        await self._process_block_range(
            max(self._last_block, self._start_block) + 1, head, {}
        )
        self._order_matched.clear()
        self._transfers.clear()
        self._save_state(full=False)

    async def run_full_index(self, start_block: int = 0):
        """Main entry point — runs continuously with catch-up + live mode."""
        self._running = True
        self._load_state()

        if start_block > 0:
            self._start_block = start_block

        if self._last_block == 0 and self._start_block == 0:
            self._start_block = 1  # Start from genesis

        head = await self.get_current_block()
        if head == 0:
            print("[Indexer] Cannot reach blockchain. Retrying...")
            await asyncio.sleep(10)
            head = await self.get_current_block()
            if head == 0:
                print("[Indexer] FATAL: cannot reach blockchain")
                return

        self._head_block = head
        last_checkpoint = max(self._last_block, 0)

        print(f"[Indexer] Chain head: {head:,} | Last indexed: {self._last_block:,}")
        print(f"[Indexer] Start block: {self._start_block}")

        # Catch-up if behind
        if self._last_block < head:
            await self._do_catchup(max(self._last_block, self._start_block), head)

        # Switch to live mode
        await self._do_live_poll()

    def stop(self):
        self._running = False
        self._save_state(full=True)
        print("[Indexer] Stopped, state saved.")

    # ── Stats / API ──────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "last_block": self._last_block,
            "start_block": self._start_block,
            "head_block": self._head_block,
            "events_total": self._events_total,
            "catching_up": self._catching_up,
            "spenders_count": len(self._cumulative_spenders),
            "earners_count": len(self._cumulative_earners),
            "mints_count": len(self._cumulative_mints),
            "matched_count": len(self._all_matched),
            "transfers_count": len(self._all_transfers),
            "running": self._running,
        }

    def get_top_spenders(self, limit: int = 10) -> list[dict]:
        return [
            {"wallet": w, "volume": v}
            for w, v in sorted(self._cumulative_spenders.items(),
                               key=lambda x: x[1], reverse=True)[:limit]
        ]

    def get_top_earners(self, limit: int = 10) -> list[dict]:
        return [
            {"wallet": w, "volume": v}
            for w, v in sorted(self._cumulative_earners.items(),
                               key=lambda x: x[1], reverse=True)[:limit]
        ]

    def get_top_minters(self, limit: int = 10) -> list[dict]:
        return [
            {"wallet": w, "mint_count": c, "volume": c * 500_000}  # estimated
            for w, c in sorted(self._cumulative_mints.items(),
                               key=lambda x: x[1], reverse=True)[:limit]
        ]

    def get_bot_farmers(self, limit: int = 10) -> list[dict]:
        """Detect wallets with many transfers received + level clustering pattern."""
        # Count transfers per receiver
        receiver_counts = defaultdict(int)
        receiver_chars = defaultdict(list)
        for t in self._all_transfers:
            to = t.get("to_addr", "")
            if to and not t.get("is_mint", False) and not to.startswith("0x0000"):
                receiver_counts[to] += 1
                if t.get("nft_type") == "character":
                    receiver_chars[to].append(t)

        # Wallets receiving many chars from same sources = consolidation
        consolidators = defaultdict(lambda: {"total_transfers": 0, "char_transfers": 0, "sources": set()})
        for t in self._all_transfers:
            to = t.get("to_addr", "")
            from_ = t.get("from_addr", "")
            if to and from_ and not from_.startswith("0x0000"):
                consolidators[to]["total_transfers"] += 1
                if t["nft_type"] == "character":
                    consolidators[to]["char_transfers"] += 1
                    consolidators[to]["sources"].add(from_)

        farmers = []
        for wallet, data in consolidators.items():
            chars = data["char_transfers"]
            sources = len(data["sources"])
            if chars >= 3 and sources >= 1:
                farmers.append({
                    "wallet": wallet,
                    "consolidations": data["total_transfers"],
                    "char_transfers": chars,
                    "unique_sources": sources,
                })

        farmers.sort(key=lambda x: x["consolidations"], reverse=True)
        return farmers[:limit]

    def get_recent_matches(self, limit: int = 20) -> list[dict]:
        """Return most recent OrderMatched events."""
        items = list(self._all_matched.values())
        items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return items[:limit]

    def get_recent_transfers(self, limit: int = 20) -> list[dict]:
        items = sorted(self._all_transfers, key=lambda x: x.get("timestamp", 0), reverse=True)
        return items[:limit]

    def find_snipe(self, tx_hash: str) -> dict:
        """Check if a specific transaction was a snipe."""
        match = self._all_matched.get(tx_hash)
        if not match:
            return {}
        return {
            **match,
            "is_snipe": match.get("instant_buy", False),
        }


# Singleton
blockchain_indexer = BlockchainIndexer()
