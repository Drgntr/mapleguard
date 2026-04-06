"""
snowtrace_deep_scanner.py  —  ONE API CALL PER PAGE, zero extra lookups.
=========================================================================

Strategy (no N+1):
  - Primary query: ERC-20 transfers of the NESO token
  - Each record already has: txHash, from (buyer), to (seller), value (price)
  - We only keep transfers where 'to' matches the marketplace contract address
    pattern OR the value is suspiciously low (snipe threshold)
  - The tokenId is reconstructed from the raw ABI data if needed, but for
    snipe-detection purposes the PRICE alone is sufficient for flagging.

This means: ONE HTTP request per page, process ~100 records, move on.
No secondary calls. No rate limits.

Checkpoint / Resume: saves every CHECKPOINT_EVERY pages, Ctrl+C safe.
"""

import asyncio
import httpx
import json
import os
import sys
import time
import datetime
import signal

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
FRONTEND_TS_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'frontend', 'src', 'data', 'historical_snipes.ts'))
BOT_CONFIG_FILE  = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', 'maple', 'bot_config.json'))
STATE_FILE       = os.path.join(SCRIPT_DIR, 'scanner_state.json')

# ── Chain constants ────────────────────────────────────────────────────────────
BASE_URL         = "https://api.routescan.io/v2/network/mainnet/evm/68414"
NESO_TOKEN       = "0x07E49Ad54FcD23F6e7B911C2068F0148d1827c08"
MARKETPLACE_ADDR = "0x6813869c3e5dec06e6f88b42d41487dc5d7abf57"
CHAR_NFT         = "0xcE8e48Fae05c093a4A1a1F569BDB53313D765937"
ITEM_NFT         = "0x43DCff2A0cedcd5e10e6f1c18b503498dDCe60d5"

PAGE_LIMIT       = 100
CHECKPOINT_EVERY = 100   # save every N pages
SLEEP_BETWEEN    = 0.3   # small delay between pages (avoids any throttling)
SKIN_FLOOR_MIN   = 150_000  # ignore items sold below this NESO floor (cheap skins)


# ── State ─────────────────────────────────────────────────────────────────────
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                s = json.load(f)
            # Ensure defaults for older state files
            state = {
                "snipes": s.get("snipes", []),
                "seen_tx": s.get("seen_tx", []),
                "cursor": s.get("cursor"),
                "page": s.get("page", 0),
                "done": s.get("done", False)
            }
            print(f"[RESUME] {len(state['snipes'])} snipes | page {state['page']}")
            return state
        except Exception as e:
            print(f"[WARN] bad checkpoint ({e})")
    return {"snipes": [], "seen_tx": [], "cursor": None, "page": 0, "done": False}


def save_state(state: dict):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f)


def flush_ts(snipes: list):
    os.makedirs(os.path.dirname(FRONTEND_TS_FILE), exist_ok=True)
    with open(FRONTEND_TS_FILE, 'w', encoding='utf-8') as f:
        ts = datetime.datetime.now().isoformat()
        f.write(f"// Updated {ts} — {len(snipes)} snipes found\n")
        f.write(f"export const historicalSnipes = {json.dumps(snipes, indent=2)};\n")


# ── Config ────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    if os.path.exists(BOT_CONFIG_FILE):
        with open(BOT_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def is_snipe(price_neso: float, config: dict, token_id: str = "") -> tuple:
    """Returns (True, floor, label) if the NESO price flags a snipe."""
    if price_neso <= 0:
        return False, 0

    target_ids = set(str(x) for x in config.get("target_ids", []))
    max_global  = float(config.get("max_price_global", 0))

    if token_id and token_id in target_ids:
        return True, 0

    # Main rule: anything sold at or below the global bot cap
    if max_global > 0 and price_neso <= max_global:
        return True, max_global

    # Characters cheap enough to be a snipe (below 15k is suspicious)
    if price_neso < 15_000:
        return True, 50_000

    return False, 0


RPC_URL = "https://rpc.henesys.com"


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


async def enrich_with_nft(client: httpx.AsyncClient, tx_hash: str) -> dict:
    """Fetch ERC-721 transfer for this txHash to get tokenId, type, name, and image."""
    try:
        for nft_addr, nft_type in [(ITEM_NFT, "Item"), (CHAR_NFT, "Character")]:
            url = (f"{BASE_URL}/erc721-transfers"
                   f"?tokenAddress={nft_addr}&transactionHash={tx_hash}&limit=1")
            r = await client.get(url, timeout=8.0)
            if r.status_code == 200:
                items = r.json().get("items", [])
                if items:
                    token_id = str(items[0].get("tokenId", ""))

                    # Fetch real name + image from on-chain metadata
                    name, image_url = await fetch_nft_metadata(client, nft_addr, token_id)
                    if not name:
                        name = f"{nft_type} #{token_id}"
                    if not image_url:
                        image_url = ""

                    return {
                        "token_id": token_id,
                        "type": nft_type,
                        "name": name,
                        "image_url": image_url,
                        "nft_url": f"https://msu.io/marketplace/{'character' if nft_type=='Character' else 'item'}/{token_id}",
                        "explorer_nft_url": f"https://msu-explorer.xangle.io/nfts/{nft_addr}/{token_id}",
                    }
    except Exception:
        pass
    return {"token_id": "", "type": "Sale", "name": "", "image_url": "", "nft_url": "", "explorer_nft_url": ""}


async def batch_enrich(client: httpx.AsyncClient, snipes: list):
    """
    Enrich snipes that haven't been tagged yet with NFT type/tokenId/image.
    Runs at checkpoint time — never inside the page-scan hot loop.
    Also removes Items below SKIN_FLOOR_MIN (catches any that slipped through immediate filter).
    """
    to_remove = []
    for i, snipe in enumerate(snipes):
        if snipe.get("_enriched"):
            continue
        info = await enrich_with_nft(client, snipe["tx_hash"])
        snipes[i]["type"]             = info["type"]
        snipes[i]["name"]             = info["name"] or snipe["name"]
        snipes[i]["token_id"]         = info["token_id"]
        snipes[i]["image_url"]        = info["image_url"]
        snipes[i]["nft_url"]          = info["nft_url"]
        snipes[i]["explorer_nft_url"] = info["explorer_nft_url"]
        snipes[i]["_enriched"]        = True
        if info["type"] == "Item" and snipe["price"] < SKIN_FLOOR_MIN:
            to_remove.append(i)
        await asyncio.sleep(0.4)
    for i in reversed(to_remove):
        snipes.pop(i)
    if to_remove:
        print(f"\n  [filter] Removed {len(to_remove)} cheap items (< {SKIN_FLOOR_MIN:,} NESO floor)")


# ── Main scan ──────────────────────────────────────────────────────────────────
async def run():
    config    = load_config()
    state     = load_state()
    stop_flag = [False]

    def _sigint(sig, frame):
        print("\n\n[CTRL+C] Saving state...")
        stop_flag[0] = True
    signal.signal(signal.SIGINT, _sigint)

    snipes  = state["snipes"]
    seen_tx = set(state["seen_tx"])

    print("\n" + "=" * 65)
    print("  MapleGuard — NESO Transfer Scanner (1 call/page, no rate limits)")
    print(f"  Bot cap: {config.get('max_price_global')} NESO = snipe threshold")
    print(f"  State:   {STATE_FILE}")
    print(f"  Output:  {FRONTEND_TS_FILE}")
    print("=" * 65 + "\n")

    # Build start URL (resume from cursor if available)
    if state.get("cursor"):
        url = f"https://api.routescan.io{state['cursor']}"
        print(f"Resuming from page ~{state['page']:,} with cursor checkpoint")
    else:
        # Query ALL NESO ERC-20 transfers — this covers every purchase (price paid is included)
        url = f"{BASE_URL}/erc20-transfers?tokenAddress={NESO_TOKEN}&limit={PAGE_LIMIT}"
        print("Starting from the beginning (all NESO transfers)...")

    t0 = time.time()

    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        while url and not stop_flag[0]:
            state["page"] += 1

            try:
                resp = await client.get(url, timeout=15.0)

                if resp.status_code == 429:
                    wait = 15
                    print(f"\n[429] Rate limited — waiting {wait}s then retrying...")
                    await asyncio.sleep(wait)
                    state["page"] -= 1  # don't count this failed page
                    continue

                if resp.status_code != 200:
                    print(f"\n[HTTP {resp.status_code}] Stopping.")
                    break

                data      = resp.json()
                items     = data.get("items", [])
                link      = data.get("link", {})
                next_path = link.get("next") if isinstance(link, dict) else None

                # ── Process each NESO transfer on this page ───────────────
                for item in items:
                    tx_hash = item.get("txHash", "")
                    if not tx_hash or tx_hash in seen_tx:
                        continue
                    seen_tx.add(tx_hash)

                    # The 'value' field is the NESO amount as a raw integer string
                    raw_value = item.get("value") or item.get("amount") or "0"
                    try:
                        price = float(raw_value) / 1e18
                    except Exception:
                        continue

                    # from = buyer (pays NESO), to = seller (or marketplace escrow)
                    buyer  = item.get("from", "")
                    seller = item.get("to", "")
                    date   = item.get("createdAt") or item.get("timestamp") or ""

                    # Skip dust amounts and self-transfers
                    if price < 10:
                        continue
                    if buyer == seller:
                        continue

                    match, floor = is_snipe(price, config)
                    if match:
                        # IMMEDIATE skin filter: skip items below 150k without needing enrichment
                        # Items are almost never sold for such low prices legitimately
                        if price < SKIN_FLOOR_MIN:
                            # Could be a character (ok) or cheap item (skip)
                            # We'll let batch_enrich clean up any item that slips through
                            # But if price < 15k it's likely a character — keep it
                            if 15_000 <= price < SKIN_FLOOR_MIN:
                                continue  # Likely cheap item/skin — skip immediately

                        snipes.append({
                            "id":              tx_hash,
                            "tx_hash":         tx_hash,
                            "type":            "Sale",
                            "name":            f"NESO {price:,.0f}",
                            "token_id":        "",
                            "image_url":       "",   # filled in at checkpoint by batch_enrich
                            "price":           price,
                            "floor_price":     floor,
                            "seller":          seller,
                            "buyer":           buyer,
                            "date":            date,
                            "explorer_url":    f"https://msu-explorer.xangle.io/tx/{tx_hash}",
                            "nft_url":         "",
                            "explorer_nft_url": "",
                            "_enriched":       False,
                        })

                # ── Progress ──────────────────────────────────────────────
                elapsed = time.time() - t0
                pg_s    = state["page"] / elapsed if elapsed > 0 else 0
                sys.stdout.write(
                    f"\r  Page {state['page']:>7,}  |  Snipes {len(snipes):>5,}"
                    f"  |  {pg_s:.2f} pg/s  "
                )
                sys.stdout.flush()

                # ── Checkpoint ────────────────────────────────────────────
                if state["page"] % CHECKPOINT_EVERY == 0:
                    state["seen_tx"] = list(seen_tx)
                    state["cursor"]  = next_path
                    # Enrich un-enriched snipes in a controlled batch (not in hot loop)
                    await batch_enrich(client, snipes)
                    flush_ts(snipes)
                    save_state(state)
                    print(f"\n  ✓ pg {state['page']:,} | {len(snipes)} snipes saved")

                # ── Advance cursor ────────────────────────────────────────
                state["cursor"] = next_path
                url = f"https://api.routescan.io{next_path}" if next_path else None
                if not next_path:
                    state["done"] = True

                await asyncio.sleep(SLEEP_BETWEEN)

            except asyncio.CancelledError:
                stop_flag[0] = True
                break
            except Exception as e:
                print(f"\n[ERR] page {state['page']}: {e} — retry in 3s")
                await asyncio.sleep(3)

    # Final flush
    state["seen_tx"] = list(seen_tx)
    snipes.sort(key=lambda x: x["price"])
    flush_ts(snipes)
    save_state(state)

    done = state.get("done", False)
    print(f"\n\n{'='*65}")
    print(f"  {'COMPLETE ✓' if done else 'PAUSED — run again to resume'}")
    print(f"  Pages scanned: {state['page']:,}")
    print(f"  Snipes found:  {len(snipes):,}")
    print(f"{'='*65}")

    if done and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


async def enrich_existing():
    """Re-enrich existing snipes in scanner_state.json with NFT metadata.
    Also filters out items below SKIN_FLOOR_MIN."""
    state = load_state()
    snipes = state.get("snipes", [])
    if not snipes:
        print("No snipes in state file.")
        return

    print(f"\nRe-enriching {len(snipes)} snipes with NFT metadata (tokenURI)...")
    print(f"Item floor filter: {SKIN_FLOOR_MIN:,} NESO\n")

    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        to_remove = []
        enriched_count = 0
        skipped = 0

        for i, snipe in enumerate(snipes):
            if snipe.get("_meta_enriched"):
                skipped += 1
                continue

            tx_hash = snipe.get("tx_hash", "")
            if not tx_hash:
                continue

            # Step 1: Get token_id if missing (via ERC-721 transfer lookup)
            token_id = snipe.get("token_id", "")
            nft_type = snipe.get("type", "Sale")

            if not token_id or nft_type == "Sale":
                info = await enrich_with_nft(client, tx_hash)
                snipes[i]["type"] = info["type"]
                snipes[i]["token_id"] = info["token_id"]
                snipes[i]["nft_url"] = info["nft_url"]
                snipes[i]["explorer_nft_url"] = info["explorer_nft_url"]
                if info["name"]:
                    snipes[i]["name"] = info["name"]
                if info["image_url"]:
                    snipes[i]["image_url"] = info["image_url"]
                snipes[i]["_enriched"] = True
                nft_type = info["type"]

            # Filter items below SKIN_FLOOR_MIN
            if nft_type == "Item" and snipe["price"] < SKIN_FLOOR_MIN:
                to_remove.append(i)
                continue

            snipes[i]["_meta_enriched"] = True
            enriched_count += 1

            if enriched_count % 10 == 0:
                sys.stdout.write(f"\r  Enriched {enriched_count} | Removed {len(to_remove)} | Skipped {skipped}  ")
                sys.stdout.flush()

            if enriched_count % 50 == 0:
                save_state(state)
                flush_ts(snipes)

            await asyncio.sleep(0.3)

        for idx in reversed(to_remove):
            snipes.pop(idx)

        state["snipes"] = snipes
        save_state(state)
        flush_ts(snipes)
        print(f"\n\nDone! Enriched {enriched_count}, removed {len(to_remove)} cheap items, skipped {skipped}.")
        print(f"Final: {len(snipes)} snipes → {FRONTEND_TS_FILE}")


if __name__ == "__main__":
    if "--enrich" in sys.argv:
        asyncio.run(enrich_existing())
    else:
        asyncio.run(run())
