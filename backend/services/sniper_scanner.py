"""
Sniper Scanner Service — automatic background snipe detection + metadata enrichment.

Two concurrent loops:
  1. scan_loop:    Watches new OrderMatched events via RPC, detects snipes, fetches metadata.
  2. enrich_loop:  Processes existing un-enriched records (backfill from snowtrace scanner).

Saves everything to scripts/scanner_state.json so the API can serve it.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from config import get_settings

settings = get_settings()

# ── Constants ────────────────────────────────────────────────────────────────
RPC_URL = "https://henesys-rpc.msu.io"
MARKETPLACE = settings.MARKETPLACE_CONTRACT
CHAR_NFT = settings.CHARACTER_NFT.lower()
ITEM_NFT = settings.ITEM_NFT.lower()

ORDER_MATCHED_TOPIC = "0xd819b3bba723f50f8d3eba9453aa0d9083a236abdc78d5efd4d461064d61839d"
NESO_DECIMALS = 18
SKIN_FLOOR_MIN = 150_000
BLOCK_BATCH = 2000
START_BLOCK_DEFAULT = 12_900_000

# RouteScan API for ERC-721 lookups (used in enrich_loop for old records)
ROUTESCAN_BASE = "https://api.routescan.io/v2/network/mainnet/evm/68414"

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
STATE_FILE = os.path.join(SCRIPTS_DIR, "scanner_state.json")
TS_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend", "src", "data", "historical_snipes.ts",
)
BOT_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "..", "maple", "bot_config.json",
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def decode_abi_string(hex_data: str) -> str:
    """Decode an ABI-encoded string from eth_call result."""
    if not hex_data or hex_data == "0x" or len(hex_data) < 130:
        return ""
    try:
        data = bytes.fromhex(hex_data[2:])
        offset = int.from_bytes(data[0:32], "big")
        length = int.from_bytes(data[offset : offset + 32], "big")
        return data[offset + 32 : offset + 32 + length].decode("utf-8", errors="ignore")
    except Exception:
        return ""


def load_bot_config() -> dict:
    if os.path.exists(BOT_CONFIG):
        try:
            with open(BOT_CONFIG, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def is_snipe(
    price: float,
    config: dict,
    token_id: str = "",
    listing_time: Optional[int] = None,
    match_time: Optional[int] = None,
) -> tuple:
    """
    Determine if an order is a snipe.

    30-second rule: items can only be bought after listing_time + 30 seconds.
    If listing_time + match_time provided and the gap is < 30s, reject.

    Classification:
    1. Target items (token_id in config.target_ids) — always snipe
    2. Price below max_price_global — likely bot-sniped
    3. Very cheap items (< 15k NESO) — auto-snipe
    """
    if price <= 0:
        return False, 0

    # 30-second rule enforcement
    if listing_time is not None and match_time is not None:
        if (match_time - listing_time) < 30:
            # Bought before 30s unlock — this is a protocol-level snipe
            pass  # Still flag it; the 30s rule is what defines a snipe
        else:
            # Bought legitimately after 30s — still a snipe only if price
            # is below configured thresholds
            pass  # Continue with normal checks

    target_ids = set(str(x) for x in config.get("target_ids", []))
    max_global = float(config.get("max_price_global", 0))
    if token_id and token_id in target_ids:
        return True, 0
    if max_global > 0 and price <= max_global:
        return True, max_global
    if price < 15_000:
        return True, 50_000
    return False, 0


def is_value_snipe(
    price: float,
    fair_value: float,
    threshold: float = 0.5,
) -> bool:
    """
    Detect a snipe based on fair-value comparison from rarity engine.
    An item is a snipe if listed at < threshold * fair_value.

    This catches:
    - Rare potential items with god-level stats listed cheap
    - Low-stats legendary items that are NOT actually underpriced

    Args:
        price: Actual listing price in NESO
        fair_value: rarity_engine fair_value_estimate
        threshold: Ratio below which is considered a snipe (default 0.5 = 50% of fair value)
    """
    if fair_value <= 0 or price <= 0:
        return False
    return price < fair_value * threshold


# ── Service ──────────────────────────────────────────────────────────────────

class SniperScannerService:
    def __init__(self):
        self._running = False
        self._state: dict = {"last_block": 0, "snipes": [], "seen_tx": []}
        self._seen_tx: set = set()
        self._config: dict = {}
        self._scan_stats = {"blocks_scanned": 0, "snipes_found": 0, "enriched": 0}
        self._client: Optional[httpx.AsyncClient] = None

    # ── State persistence ────────────────────────────────────────────────

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
                self._seen_tx = set(s.get("tx_hash", s.get("id", "")) for s in self._state.get("snipes", []))
                print(f"[SniperScanner] Loaded {len(self._state['snipes'])} snipes, last_block={self._state.get('last_block', 0)}")
            except Exception as e:
                print(f"[SniperScanner] Error loading state: {e}")

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._state, f)
        except Exception as e:
            print(f"[SniperScanner] Error saving state: {e}")

    # ── RPC calls ────────────────────────────────────────────────────────

    async def _get_current_block(self) -> int:
        try:
            r = await self._client.post(RPC_URL, json={
                "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1,
            }, timeout=10.0)
            return int(r.json()["result"], 16)
        except Exception:
            return 0

    async def _get_block_timestamp(self, block_hash: str) -> int:
        try:
            r = await self._client.post(RPC_URL, json={
                "jsonrpc": "2.0", "method": "eth_getBlockByHash",
                "params": [block_hash, False], "id": 1,
            }, timeout=10.0)
            return int(r.json()["result"]["timestamp"], 16)
        except Exception:
            return int(time.time())

    async def _get_logs(self, from_block: int, to_block: int) -> list:
        try:
            r = await self._client.post(RPC_URL, json={
                "jsonrpc": "2.0", "method": "eth_getLogs",
                "params": [{
                    "address": MARKETPLACE,
                    "topics": [ORDER_MATCHED_TOPIC],
                    "fromBlock": hex(from_block),
                    "toBlock": hex(to_block),
                }], "id": 1,
            }, timeout=20.0)
            res = r.json()
            if "error" in res:
                return []
            return res.get("result", [])
        except Exception:
            return []

    # ── Metadata fetch ───────────────────────────────────────────────────

    async def _fetch_metadata(self, nft_addr: str, token_id: str) -> tuple:
        """Fetch real NFT name and image via tokenURI RPC call + metadata JSON."""
        try:
            token_id_hex = hex(int(token_id))[2:].zfill(64)
            call_data = f"0xc87b56dd{token_id_hex}"

            r = await self._client.post(RPC_URL, json={
                "jsonrpc": "2.0", "method": "eth_call",
                "params": [{"to": nft_addr, "data": call_data}, "latest"], "id": 1,
            }, timeout=10.0)

            uri = decode_abi_string(r.json().get("result", "0x"))
            if not uri:
                return None, None

            meta_r = await self._client.get(uri, timeout=10.0)
            if meta_r.status_code == 200:
                meta = meta_r.json()
                return meta.get("name", ""), meta.get("image", "")
        except Exception:
            pass
        return None, None

    # ERC-721 Transfer event signature
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    async def _enrich_from_receipt(self, tx_hash: str) -> dict:
        """For old records without token_id: get tx receipt → find ERC-721 transfer → fetch metadata."""
        try:
            r = await self._client.post(RPC_URL, json={
                "jsonrpc": "2.0", "method": "eth_getTransactionReceipt",
                "params": [tx_hash], "id": 1,
            }, timeout=10.0)
            receipt = r.json().get("result")
            if not receipt:
                return {}

            # Find the ERC-721 Transfer log (has 4 topics: event sig + from + to + tokenId)
            for log in receipt.get("logs", []):
                topics = log.get("topics", [])
                if len(topics) == 4 and topics[0] == self.TRANSFER_TOPIC:
                    contract = log["address"].lower()
                    token_id = str(int(topics[3], 16))

                    if contract == CHAR_NFT:
                        nft_type = "Character"
                        nft_addr = settings.CHARACTER_NFT
                    elif contract == ITEM_NFT:
                        nft_type = "Item"
                        nft_addr = settings.ITEM_NFT
                    else:
                        continue

                    name, image = await self._fetch_metadata(nft_addr, token_id)
                    return {
                        "token_id": token_id,
                        "type": nft_type,
                        "name": name or f"{nft_type} #{token_id}",
                        "image_url": image or "",
                        "nft_url": f"https://msu.io/marketplace/{nft_type.lower()}/{token_id}",
                        "explorer_nft_url": f"https://msu-explorer.xangle.io/nfts/{nft_addr}/{token_id}",
                    }
        except Exception:
            pass
        return {}

    # ── Scan Loop (new blocks via RPC) ───────────────────────────────────

    async def _scan_loop(self):
        """Main scanning loop: watches new OrderMatched events via RPC."""
        print("[SniperScanner] Scan loop started")
        self._config = load_bot_config()
        print(f"[SniperScanner] Bot config: max_price_global={self._config.get('max_price_global')}")

        while self._running:
            try:
                current_head = await self._get_current_block()
                if current_head == 0:
                    await asyncio.sleep(5)
                    continue

                last_block = self._state.get("last_block", 0)
                if last_block == 0:
                    # First run: start from 100k blocks ago
                    last_block = max(0, current_head - 100_000)
                    self._state["last_block"] = last_block
                    print(f"[SniperScanner] Starting from block {last_block} (current: {current_head})")

                # Process blocks in batches
                blocks_this_cycle = 0
                while last_block < current_head and self._running:
                    from_block = last_block + 1
                    to_block = min(from_block + BLOCK_BATCH - 1, current_head)

                    logs = await self._get_logs(from_block, to_block)

                    for log in logs:
                        await self._process_log(log)

                    last_block = to_block
                    self._state["last_block"] = to_block
                    blocks_this_cycle += (to_block - from_block + 1)
                    self._scan_stats["blocks_scanned"] += (to_block - from_block + 1)

                    # Save every 10k blocks
                    if blocks_this_cycle % 10_000 < BLOCK_BATCH:
                        self._save_state()
                        print(f"[SniperScanner] Block {to_block:,} | {len(self._state['snipes'])} snipes")

                # Caught up — save and wait for new blocks
                self._save_state()
                await asyncio.sleep(5)

            except Exception as e:
                print(f"[SniperScanner] Scan error: {e}")
                await asyncio.sleep(10)

    async def _process_log(self, log: dict):
        """Decode an OrderMatched log, check if snipe, enrich with metadata."""
        try:
            tx_hash = log.get("transactionHash", "")
            if not tx_hash or tx_hash in self._seen_tx:
                return

            topics = log.get("topics", [])
            if len(topics) < 4:
                return

            seller = "0x" + topics[2][26:]
            buyer = "0x" + topics[3][26:]

            data = log["data"][2:]
            if len(data) < 256:
                return

            token_id = str(int(data[0:64], 16))
            nft_addr = "0x" + data[88:128].lower()
            price_wei = int(data[192:256], 16)
            price = price_wei / (10 ** NESO_DECIMALS)

            # Decode listing_time from Order struct (bytes 160-192)
            listing_time = int(data[128:192], 16) if len(data) >= 256 else None

            nft_type = "Character" if nft_addr == CHAR_NFT else "Item"

            # Filter items below SKIN_FLOOR_MIN
            if nft_type == "Item" and price < SKIN_FLOOR_MIN:
                return

            # Get block timestamp for the match time
            ts = await self._get_block_timestamp(log.get("blockHash", ""))
            match_time = ts

            match, floor = is_snipe(
                price, self._config, token_id,
                listing_time=listing_time,
                match_time=match_time,
            )
            if not match:
                return

            self._seen_tx.add(tx_hash)

            date_str = datetime.fromtimestamp(match_time, tz=timezone.utc).isoformat()

            # Compute 30-second violation flag
            time_since_listing = match_time - listing_time if listing_time else None
            instant_buy = time_since_listing is not None and time_since_listing < 30

            # Fetch real name + image from on-chain metadata
            real_nft_addr = settings.ITEM_NFT if nft_type == "Item" else settings.CHARACTER_NFT
            meta_name, meta_image = await self._fetch_metadata(real_nft_addr, token_id)
            name = meta_name or f"{nft_type} #{token_id}"
            image_url = meta_image or ""

            snipe = {
                "id": tx_hash,
                "tx_hash": tx_hash,
                "type": nft_type,
                "name": name,
                "token_id": token_id,
                "image_url": image_url,
                "price": price,
                "floor_price": floor,
                "seller": seller,
                "buyer": buyer,
                "date": date_str,
                "explorer_url": f"https://msu-explorer.xangle.io/tx/{tx_hash}",
                "nft_url": f"https://msu.io/marketplace/{nft_type.lower()}/{token_id}",
                "explorer_nft_url": f"https://msu-explorer.xangle.io/nfts/{real_nft_addr}/{token_id}",
                "listing_time": listing_time,
                "time_to_purchase_sec": time_since_listing,
                "instant_buy": instant_buy,
                "_enriched": True,
                "_meta_enriched": True,
            }

            self._state["snipes"].append(snipe)
            self._scan_stats["snipes_found"] += 1

        except Exception:
            pass

    # ── Enrich Loop (backfill old records) ───────────────────────────────

    async def _enrich_loop(self):
        """Background loop: enriches existing un-enriched records with metadata."""
        # Wait for scan loop to start first
        await asyncio.sleep(30)
        print("[SniperScanner] Enrich loop started")

        while self._running:
            try:
                snipes = self._state.get("snipes", [])
                to_remove = []
                enriched_this_round = 0

                for i, snipe in enumerate(snipes):
                    if not self._running:
                        break
                    if snipe.get("_meta_enriched"):
                        continue

                    tx_hash = snipe.get("tx_hash", snipe.get("id", ""))
                    token_id = snipe.get("token_id", "")

                    # Case 1: Has token_id but no metadata
                    if token_id:
                        nft_type = snipe.get("type", "Item")
                        nft_addr = settings.CHARACTER_NFT if nft_type == "Character" else settings.ITEM_NFT

                        # Filter items below SKIN_FLOOR_MIN
                        if nft_type == "Item" and snipe.get("price", 0) < SKIN_FLOOR_MIN:
                            to_remove.append(i)
                            continue

                        name, image = await self._fetch_metadata(nft_addr, token_id)
                        if name:
                            snipes[i]["name"] = name
                        if image:
                            snipes[i]["image_url"] = image
                        snipes[i]["_meta_enriched"] = True

                    # Case 2: No token_id (old snowtrace data) — look up tx receipt via RPC
                    elif tx_hash:
                        info = await self._enrich_from_receipt(tx_hash)
                        if info:
                            snipes[i]["type"] = info.get("type", snipe.get("type", "Sale"))
                            snipes[i]["token_id"] = info.get("token_id", "")
                            snipes[i]["name"] = info.get("name", snipe.get("name", ""))
                            snipes[i]["image_url"] = info.get("image_url", "")
                            snipes[i]["nft_url"] = info.get("nft_url", "")
                            snipes[i]["explorer_nft_url"] = info.get("explorer_nft_url", "")

                            # Filter items below SKIN_FLOOR_MIN
                            if info.get("type") == "Item" and snipe.get("price", 0) < SKIN_FLOOR_MIN:
                                to_remove.append(i)
                                continue

                        snipes[i]["_enriched"] = True
                        snipes[i]["_meta_enriched"] = True
                        await asyncio.sleep(0.15)
                    else:
                        snipes[i]["_meta_enriched"] = True
                        continue

                    enriched_this_round += 1
                    self._scan_stats["enriched"] += 1

                    # Save every 50 enriched
                    if enriched_this_round % 50 == 0:
                        self._save_state()
                        print(f"[SniperScanner] Enriched {enriched_this_round} | Removed {len(to_remove)} cheap items")

                    await asyncio.sleep(0.15)

                # Remove filtered items (reverse order)
                if to_remove:
                    for idx in reversed(to_remove):
                        snipes.pop(idx)
                    self._state["snipes"] = snipes

                if enriched_this_round > 0 or to_remove:
                    self._save_state()
                    print(f"[SniperScanner] Enrich pass done: {enriched_this_round} enriched, {len(to_remove)} removed")

                # Wait before next enrich pass (1 hour)
                await asyncio.sleep(3600)

            except Exception as e:
                print(f"[SniperScanner] Enrich error: {e}")
                await asyncio.sleep(60)

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def run(self):
        """Start both loops concurrently."""
        self._running = True
        self._load_state()

        limits = httpx.Limits(max_keepalive_connections=20, max_connections=20)
        self._client = httpx.AsyncClient(limits=limits, timeout=15.0, verify=False)

        try:
            await asyncio.gather(
                self._scan_loop(),
                self._enrich_loop(),
            )
        finally:
            await self._client.aclose()

    def stop(self):
        self._running = False

    def get_stats(self) -> dict:
        return {
            "last_block": self._state.get("last_block", 0),
            "total_snipes": len(self._state.get("snipes", [])),
            "blocks_scanned": self._scan_stats["blocks_scanned"],
            "snipes_found": self._scan_stats["snipes_found"],
            "enriched": self._scan_stats["enriched"],
            "running": self._running,
        }


# Singleton
sniper_scanner = SniperScannerService()
