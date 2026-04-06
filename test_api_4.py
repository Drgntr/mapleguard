import sys
import asyncio
import json

sys.path.append(r"c:\Scripts\Maple\MapleGuard\backend")
from services.market_data import market_data_service

async def main():
    try:
        # What happens when we pass "Warrior" to class_filter?
        chars, is_last, count = await market_data_service.fetch_characters(
            page=1, page_size=5, class_filter="Warrior", job_filter="all_jobs"
        )
        print(f"Count with Warrior: {count}, characters returned: {len(chars)}")
        for c in chars:
            print("  ", c.name, "-", c.class_name, "-", c.job_name)

        # What happens when we pass "Magician"
        chars, is_last, count = await market_data_service.fetch_characters(
            page=1, page_size=5, class_filter="Magician", job_filter="all_jobs"
        )
        print(f"Count with Magician: {count}, characters returned: {len(chars)}")
        for c in chars:
            print("  ", c.name, "-", c.class_name, "-", c.job_name)

    except Exception as e:
        print("Error:", e)

asyncio.run(main())
