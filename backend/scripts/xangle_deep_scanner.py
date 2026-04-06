from curl_cffi import requests
import json
import time
import os
import sys

# Paths
FRONTEND_TS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'src', 'data', 'historical_snipes.ts'))
BOT_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'maple', 'bot_config.json'))
TOKEN_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'maple', 'msu_tokens.json'))

XANGLE_TRADE_URL = "https://api-gateway.xangle.io/api/nft/trade/list"
HEADERS = {
    "accept": "application/json",
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/json",
    "origin": "https://msu-explorer.xangle.io",
    "referer": "https://msu-explorer.xangle.io/",
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "x-chain": "NEXON",
    "x-secret-key": "21203760ac9d08ecb5bc85c25553d7d14fc3bdaea0feab409baa7bd62c18d84897308db8845a02c507f39fccb83e1ac061b1e2e36f54aa0e6dd11d8afdf58429",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
}

def load_config():
    if os.path.exists(BOT_CONFIG_FILE):
        with open(BOT_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def is_snipe(trade, config):
    try:
        # Xangle trade response parsing
        price_wei = float(trade.get("PRICE", 0))
        if price_wei <= 0: return False
        
        price = price_wei / 1e18
        name = trade.get("TKNNM", "")
        token_id = str(trade.get("TKNID", ""))
        
        # Determine Character vs Item by Token ID length
        is_character = len(token_id) > 20
        
        target_items = config.get("target_items", {})
        target_chars = config.get("target_characters", {})
        max_global = config.get("max_price_global", 0)
        
        # Exact match logic from zero_latency_sniper.py
        if token_id in config.get("target_ids", []):
            return True, "Target ID Match"
            
        if not is_character and name in target_items and price <= target_items[name]:
            return True, target_items[name]
            
        if is_character and name in target_chars and price <= target_chars[name]:
            return True, target_chars[name]
            
        if max_global > 0 and price <= max_global and price > 0:
            # We enforce a hard floor for random items so we don't spam 1 NESO trash
            # Only flag if it's over 10 NESO global floor or it's a known character
            if is_character and price < 50000:
                pass # Characters usually > 50k
            elif price < 10.0:
                return False, 0
                
            return True, max_global
            
        # Add a baseline hardcoded character rule to catch extreme dumps
        if is_character and price > 0 and price < 15000:
            return True, 50000
            
        return False, 0
    except Exception as e:
        return False, 0

def scan_xangle_trades(pages=20):
    config = load_config()
    snipes = []
    
    print(f"Starting Deep Scan of {pages} Xangle Trade Pages...")
    print(f"Using Bot Config: Global Max={config.get('max_price_global')}")
    
    with requests.Session(impersonate="chrome110") as client:
        # Load tokens
        cookies = {}
        if os.path.exists(TOKEN_FILE):
             try:
                 with open(TOKEN_FILE, 'r') as f:
                     tokens = json.load(f)
                     if "jwt_token" in tokens:
                         cookies["msu_wat"] = tokens["jwt_token"]
             except Exception: pass

        for page in range(1, pages + 1):
            sys.stdout.write(f"\rScanning Page {page}/{pages}...")
            sys.stdout.flush()
            
            payload = {"page": page, "size": 100}
            try:
                # Try the trade endpoint
                resp = client.post(XANGLE_TRADE_URL, json=payload, headers=HEADERS, cookies=cookies)
                if resp.status_code != 200:
                    # Fallback to transfer endpoint
                    resp = client.post("https://api-gateway.xangle.io/api/nft/transfer/list", json=payload, headers=HEADERS, cookies=cookies)
                
                if resp.status_code == 200:
                    data = resp.json()
                    trades = data.get("LIST", [])
                    if not trades:
                        break
                        
                    for t in trades:
                        # Price is either PRICE or AMOUNT based on endpoint
                        raw_price = t.get("PRICE") or t.get("AMOUNT", "0")
                        t["PRICE"] = raw_price
                        
                        snipe_match, floor = is_snipe(t, config)
                        if snipe_match:
                            snipes.append({
                                "id": t.get("TXHASH", "") + "_" + str(t.get("TKNID", "")),
                                "tx_hash": t.get("TXHASH", ""),
                                "type": "Character" if len(str(t.get("TKNID", ""))) > 20 else "Item",
                                "name": t.get("TKNNM", "Unknown"),
                                "token_id": t.get("TKNID", ""),
                                "price": float(t["PRICE"]) / 1e18,
                                "floor_price": floor if isinstance(floor, (int, float)) else 0,
                                "seller": t.get("ADDRSFROMINFO", {}).get("ADDR", "Unknown"),
                                "buyer": t.get("ADDRSTOINFO", {}).get("ADDR", "Unknown"),
                                "date": t.get("CREATEDAT", "")
                            })
                else:
                    print(f"\nAPI Error: {resp.status_code}")
                    break
            except Exception as e:
                print(f"\nRequest Error: {e}")
                
            time.sleep(0.5)
            
    print(f"\nScan Complete! Found {len(snipes)} historical sniped items.")
    
    # Write to static TS file
    os.makedirs(os.path.dirname(FRONTEND_TS_FILE), exist_ok=True)
    with open(FRONTEND_TS_FILE, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by Xangle Deep Scanner\n")
        f.write(f"export const historicalSnipes = {json.dumps(snipes, indent=2)};\n")
        
    print(f"Saved directly to {FRONTEND_TS_FILE}")

if __name__ == "__main__":
    scan_xangle_trades(pages=50) # Scan 50 pages equivalent to 5000 recent trades
