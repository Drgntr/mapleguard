from curl_cffi import requests
import json

wallet = "0xd6435cB8f2761028234Ec69E3ac16cCA53022e9"

headers = {
    "accept": "application/json",
    "origin": "https://msu.io",
    "referer": "https://msu.io/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/146.0.0.0",
}

urls = [
    f"https://api.msu.io/marketplace/explore/characters", # testing with owner filter
    f"https://api.msu.io/user/{wallet}/characters",
    f"https://api.msu.io/marketplace/user/{wallet}/nfts",
    f"https://msu.io/api/user/{wallet}",
    f"https://api-gateway.xangle.io/api/nft/wallet/{wallet}/list",
]

for url in urls:
    print(f"\n--- Testing {url} ---")
    try:
        # For the explore endpoint, we test if it accepts 'owner' in filter
        if "explore/characters" in url:
            body = {"filter": {"ownerAddress": wallet}, "paginationParam": {"pageNo": 1, "pageSize": 50}}
            r = requests.post(url, json=body, headers=headers, impersonate="chrome")
        else:
            r = requests.get(url, headers=headers, impersonate="chrome")
            
        print("Status:", r.status_code)
        if r.status_code == 200:
            print(r.text[:300])
    except Exception as e:
        print("Error:", e)
