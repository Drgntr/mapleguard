import os
import sys
from curl_cffi import requests

sys.path.append("C:\\Scripts\\Maple\\MapleGuard\\backend")
from config import get_settings

settings = get_settings()

headers = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "origin": "https://msu.io",
    "referer": "https://msu.io/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
}

print(f"MSU_API_BASE: {settings.MSU_API_BASE}")
print(f"MSU_NAVIGATOR_BASE: {settings.MSU_NAVIGATOR_BASE}")

endpoints = [
    f"{settings.MSU_NAVIGATOR_BASE}/msu-stats/search?keyword=chupper",
    f"{settings.MSU_NAVIGATOR_BASE}/search?keyword=chupper",
    f"{settings.MSU_API_BASE}/navigator/search?keyword=chupper",
    f"{settings.MSU_API_BASE}/search?keyword=chupper",
    f"https://api.msu.io/search?keyword=chupper",
    f"https://api.msu.io/msu-stats/search?keyword=chupper"
]

for ep in endpoints:
    print(f"\n--- Testing {ep} ---")
    try:
        r = requests.get(ep, headers=headers, impersonate="chrome")
        print("Status:", r.status_code)
        if r.status_code == 200:
            print("Body:", r.text[:300])
    except Exception as e:
        print("Error:", e)
