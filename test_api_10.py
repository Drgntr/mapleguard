import sys
import asyncio
import json

sys.path.append(r"c:\Scripts\Maple\MapleGuard\backend")
from services.market_data import market_data_service

async def main():
    url = "https://msu.io/marketplace/api/marketplace/explore/characters"
    body = {
        "filter": {"price": {"min": 0, "max": 10000000000}, "level": {"min": 0, "max": 300}, "class": "all_classes"},
        "paginationParam": {"pageNo": 1, "pageSize": 1},
    }
    char_headers = {
        "accept": "*/*",
        "accept-language": "en-US",
        "content-type": "application/json",
        "origin": "https://msu.io",
        "referer": "https://msu.io/marketplace/characters",
    }
    
    data = market_data_service._post(url, body, char_headers)
    if "characters" in data and len(data["characters"]) > 0:
        char = data["characters"][0]
        # Just dump the raw character object!
        with open("test_api_10_out.json", "w") as f:
            json.dump(char, f, indent=2)

asyncio.run(main())
