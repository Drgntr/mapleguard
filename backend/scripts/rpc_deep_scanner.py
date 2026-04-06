import asyncio
import httpx
import json
import os
import sys
import time
import signal
from datetime import datetime
from decimal import Decimal

# --- Constants & Contracts ---
RPC_URL = "https://rpc.henesys.com"
MARKETPLACE = "0x6813869c3e5dec06e6f88b42d41487dc5d7abf57"
ORDER_MATCHED_TOPIC = "0xd819b3bba723f50f8d3eba9453aa0d9083a236abdc78d5efd4d461064d61839d"

CHAR_NFT = "0xcE8e48Fae05c093a4A1a1F569BDB53313D765937".lower()
ITEM_NFT = "0x43DCff2A0cedcd5e10e6f1c18b503498dDCe60d5".lower()

# 1 NESO = 1e18 wei
NESO_DECIMALS = 18

# Constants for detection
SKIN_FLOOR_MIN = 150_000

# File Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "bot_config.json")
STATE_FILE = os.path.join(SCRIPT_DIR, "rpc_scanner_state.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "..", "frontend", "src", "data", "historical_snipes.ts")

# ── Loaders ────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_block": 12900000, "snipes": []}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def save_ts_output(state: dict):
    ts_content = "export const historicalSnipes = " + json.dumps(state["snipes"], indent=2) + ";\n"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(ts_content)

# ── Logic ──────────────────────────────────────────────────────────────────────
def is_snipe(price_neso: float, config: dict, token_id: str) -> tuple:
    """Returns (True, floor_price) if it's a snipe."""
    if price_neso <= 0:
        return False, 0

    target_ids = set(str(x) for x in config.get("target_ids", []))
    max_global = float(config.get("max_price_global", 0))

    if token_id in target_ids:
        return True, 0

    if max_global > 0 and price_neso <= max_global:
        return True, max_global

    if price_neso < 15_000:
        return True, 50_000

    return False, 0

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


async def fetch_nft_metadata(client: httpx.AsyncClient, nft_addr: str, token_id: str) -> tuple:
    """Fetch real NFT name and image via tokenURI RPC call + metadata JSON."""
    try:
        token_id_hex = hex(int(token_id))[2:].zfill(64)
        call_data = f"0xc87b56dd{token_id_hex}"

        r = await client.post(RPC_URL, json={
            "jsonrpc": "2.0", "method": "eth_call",
            "params": [{"to": nft_addr, "data": call_data}, "latest"], "id": 1,
        }, timeout=10.0)

        uri = decode_abi_string(r.json().get("result", "0x"))
        if not uri:
            return None, None

        meta_r = await client.get(uri, timeout=10.0)
        if meta_r.status_code == 200:
            meta = meta_r.json()
            return meta.get("name", ""), meta.get("image", "")
    except Exception:
        pass
    return None, None

# ── Web3 RPC Calls ─────────────────────────────────────────────────────────────
async def get_current_block(client: httpx.AsyncClient) -> int:
    try:
        r = await client.post(RPC_URL, json={"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1})
        return int(r.json()["result"], 16)
    except Exception:
        return 0

async def get_block_timestamp(client: httpx.AsyncClient, block_hash: str) -> int:
    try:
        r = await client.post(RPC_URL, json={"jsonrpc":"2.0","method":"eth_getBlockByHash","params":[block_hash, False],"id":1})
        return int(r.json()["result"]["timestamp"], 16)
    except Exception:
        return int(time.time())

async def get_logs(client: httpx.AsyncClient, from_block: int, to_block: int) -> list:
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{
            "address": MARKETPLACE,
            "topics": [ORDER_MATCHED_TOPIC],
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block)
        }],
        "id": 1
    }
    for attempt in range(5):
        try:
            r = await client.post(RPC_URL, json=payload, timeout=20.0)
            res = r.json()
            if "error" in res:
                if "block range is too wide" in str(res["error"]):
                    return [] # Let caller handle splitting
                print(f"\n[RPC Error] {res['error']}")
                await asyncio.sleep(2)
                continue
            return res.get("result", [])
        except Exception as e:
            if attempt == 4: raise e
            await asyncio.sleep(2)
    return []

# ── Main ───────────────────────────────────────────────────────────────────────
async def run():
    config = load_config()
    state = load_state()
    stop_flag = [False]

    def _sigint(sig, frame):
        print("\n\n[CTRL+C] Saving state...")
        stop_flag[0] = True

    signal.signal(signal.SIGINT, _sigint)

    print("=================================================================")
    print("  MapleGuard — Web3 RPC Sniper Scanner (Zero Rate Limits)")
    print(f"  Bot cap: {config.get('max_price_global', 2000.0)} NESO = snipe threshold")
    print(f"  State:   {STATE_FILE}")
    print(f"  Output:  {OUTPUT_FILE}")
    print("=================================================================\n")

    limits = httpx.Limits(max_keepalive_connections=50, max_connections=50)
    async with httpx.AsyncClient(limits=limits) as client:
        current_head = await get_current_block(client)
        if state["last_block"] == 0 or state["last_block"] > current_head:
            state["last_block"] = max(0, current_head - 100000)
            print(f"Starting from 100k blocks ago (Block {state['last_block']})...\n")
        else:
            print(f"Resuming from block {state['last_block']} (Current Head: {current_head})...\n")

        # To avoid overloading the RPC node, fetch 5000 blocks at a time
        BLOCK_BATCH = 2000
        t0 = time.time()
        blocks_processed = 0

        while state["last_block"] < current_head and not stop_flag[0]:
            from_block = state["last_block"] + 1
            to_block = min(from_block + BLOCK_BATCH - 1, current_head)

            logs = await get_logs(client, from_block, to_block)
            
            # If the RPC complains about block range, fallback to smaller chunks
            if logs == [] and from_block != to_block:
                pass

            snipes_found_in_batch = 0

            # Process logs
            for log in logs:
                try:
                    seller = "0x" + log["topics"][2][26:] if len(log.get("topics", [])) > 2 else "Unknown"
                    buyer  = "0x" + log["topics"][3][26:] if len(log.get("topics", [])) > 3 else "Unknown"
                    
                    data = log["data"][2:] # Remove 0x
                    if len(data) < 256: continue
                    
                    token_id_hex = data[0:64]
                    nft_addr_hex = data[64:128]
                    # token_addr_hex = data[128:192]
                    token_amt_hex = data[192:256]
                    
                    token_id = str(int(token_id_hex, 16))
                    nft_addr = "0x" + nft_addr_hex[24:].lower()
                    price_wei = int(token_amt_hex, 16)
                    price = price_wei / (10 ** NESO_DECIMALS)
                    
                    nft_type = "Character" if nft_addr == CHAR_NFT else "Item"

                    # Skip items (outfits/skins) below SKIN_FLOOR_MIN
                    if nft_type == "Item" and price < SKIN_FLOOR_MIN:
                        continue

                    match, floor = is_snipe(price, config, token_id)
                    if match:
                        tx_hash = log["transactionHash"]
                        ts = await get_block_timestamp(client, log["blockHash"])
                        date_str = datetime.fromtimestamp(ts).isoformat() + "Z"

                        # Fetch real name + image from on-chain metadata
                        real_nft_addr = ITEM_NFT if nft_type == "Item" else CHAR_NFT
                        meta_name, meta_image = await fetch_nft_metadata(client, real_nft_addr, token_id)
                        name = meta_name or f"{nft_type} #{token_id}"
                        image_url = meta_image or ""

                        state["snipes"].append({
                            "id":              tx_hash,
                            "tx_hash":         tx_hash,
                            "type":            nft_type,
                            "name":            name,
                            "token_id":        token_id,
                            "image_url":       image_url,
                            "price":           price,
                            "floor_price":     floor,
                            "seller":          seller,
                            "buyer":           buyer,
                            "date":            date_str,
                            "explorer_url":    f"https://msu-explorer.xangle.io/tx/{tx_hash}",
                            "nft_url":         f"https://msu.io/marketplace/{nft_type.lower()}/{token_id}",
                            "explorer_nft_url": f"https://msu-explorer.xangle.io/nfts/{real_nft_addr}/{token_id}",
                            "_enriched":       True,
                        })
                        snipes_found_in_batch += 1
                except Exception as e:
                    pass

            # Update state
            state["last_block"] = to_block
            blocks_processed += (to_block - from_block + 1)
            
            # UI
            elapsed = time.time() - t0
            blk_s = blocks_processed / elapsed if elapsed > 0 else 0
            sys.stdout.write(
                f"\r  Block {to_block:>8,}  |  Snipes {len(state['snipes']):>5,}"
                f"  |  {blk_s:.0f} blk/s  "
            )
            sys.stdout.flush()

            # Save sporadically
            if blocks_processed % 10000 < BLOCK_BATCH:
                state["snipes"].sort(key=lambda x: x["date"], reverse=True)
                save_state(state)
                save_ts_output(state)
            
            if to_block >= current_head - BLOCK_BATCH:
                current_head = await get_current_block(client)
                if current_head <= to_block:
                    await asyncio.sleep(2)

    # Final save
    print("\n\nFinished/Stopped. Saving final history...")
    state["snipes"].sort(key=lambda x: x["date"], reverse=True)
    save_state(state)
    save_ts_output(state)
    print("Done! Restart scanner to continue watching live blocks.")

async def enrich_existing():
    """Re-enrich existing snipes from state file with NFT metadata (name + image).
    Also filters out items below SKIN_FLOOR_MIN."""
    state = load_state()
    snipes = state.get("snipes", [])
    if not snipes:
        print("No snipes in state file. Run the scanner first.")
        return

    print(f"\nEnriching {len(snipes)} snipes with NFT metadata...")
    print(f"Item floor filter: {SKIN_FLOOR_MIN:,} NESO\n")

    limits = httpx.Limits(max_keepalive_connections=20, max_connections=20)
    async with httpx.AsyncClient(limits=limits, timeout=15.0) as client:
        to_remove = []
        enriched_count = 0

        for i, snipe in enumerate(snipes):
            if snipe.get("_meta_enriched"):
                continue

            token_id = snipe.get("token_id", "")
            if not token_id:
                continue  # Can't enrich without token_id

            # Determine NFT contract from type
            nft_type = snipe.get("type", "Item")
            nft_addr = CHAR_NFT if nft_type == "Character" else ITEM_NFT

            # Filter items below SKIN_FLOOR_MIN
            if nft_type == "Item" and snipe["price"] < SKIN_FLOOR_MIN:
                to_remove.append(i)
                continue

            name, image = await fetch_nft_metadata(client, nft_addr, token_id)
            if name:
                snipes[i]["name"] = name
            if image:
                snipes[i]["image_url"] = image
            snipes[i]["_meta_enriched"] = True
            enriched_count += 1

            if (enriched_count) % 20 == 0:
                sys.stdout.write(f"\r  Enriched {enriched_count} / {len(snipes)}  ")
                sys.stdout.flush()

            # Save every 100 enriched
            if enriched_count % 100 == 0:
                save_state(state)
                save_ts_output(state)

            await asyncio.sleep(0.15)

        # Remove filtered items
        for idx in reversed(to_remove):
            snipes.pop(idx)

        state["snipes"] = snipes
        save_state(state)
        save_ts_output(state)
        print(f"\n\nDone! Enriched {enriched_count}, removed {len(to_remove)} cheap items.")
        print(f"Final: {len(snipes)} snipes saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        if "--enrich" in sys.argv:
            asyncio.run(enrich_existing())
        else:
            asyncio.run(run())
    except KeyboardInterrupt:
        pass
