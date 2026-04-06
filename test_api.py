import sys
import os

sys.path.append(r"c:\Scripts\Maple\MapleGuard\backend")
from services.market_data import market_data_service

import asyncio

async def main():
    try:
        # Test class string
        chars, _, _ = await market_data_service.fetch_characters(
            page=1, page_size=5, class_filter="Warrior", job_filter="all_jobs"
        )
        print("STRING classfilter Warrior count:", len(chars))

        # Check what classes are in the return
        classes = set(c.class_name for c in chars)
        print("Classes found (STRING):", classes)
    except Exception as e:
        print("STRING err:", e)

    try:
        # Test class array
        class MarketDataTestService(market_data_service.__class__):
            async def fetch_test(self):
                url = "https://api.msu.io/marketplace/explore/characters"
                body = {
                    "filter": {
                        "price": {"min": 0, "max": 10000000000},
                        "level": {"min": 0, "max": 300},
                        "class": ["Warrior"]
                    },
                    "paginationParam": {
                        "pageNo": 1,
                        "pageSize": 5,
                    },
                }
                char_headers = {
                    "accept": "*/*",
                    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "content-type": "application/json",
                    "origin": "https://msu.io",
                    "referer": "https://msu.io/",
                }
                data = self._post(url, body, char_headers)
                return len(data.get("characters", []))

        t = MarketDataTestService()
        res = await t.fetch_test()
        print("ARRAY classfilter ['Warrior'] count:", res)
    except Exception as e:
        print("ARRAY err:", e)

    try:
        # Test class array enum
        class MarketDataTestService(market_data_service.__class__):
            async def fetch_test(self):
                url = "https://api.msu.io/marketplace/explore/characters"
                body = {
                    "filter": {
                        "price": {"min": 0, "max": 10000000000},
                        "level": {"min": 0, "max": 300},
                        "class": ["Class_Warrior"]
                    },
                    "paginationParam": {
                        "pageNo": 1,
                        "pageSize": 5,
                    },
                }
                char_headers = {
                    "accept": "*/*",
                    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "content-type": "application/json",
                    "origin": "https://msu.io",
                    "referer": "https://msu.io/",
                }
                data = self._post(url, body, char_headers)
                return len(data.get("characters", []))

        t = MarketDataTestService()
        res = await t.fetch_test()
        print("ARRAY classfilter ['Class_Warrior'] count:", res)
    except Exception as e:
        print("ARRAY Class_Warrior err:", e)

asyncio.run(main())
