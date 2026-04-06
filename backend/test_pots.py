import asyncio
import sys
import json
from services.market_data import market_data_service

async def test():
    # Fetch random high level character from recently-listed or explore
    chars, _, _ = await market_data_service.fetch_characters(page=1, page_size=10, level_min=200)
    for c in chars:
        print(f"Checking {c.nickname}...")
        details = await market_data_service.fetch_character_detail(c.token_id)
        if not details: continue
        for item in details.equipped_items:
            if item.slot.lower() == 'emblem' or 'emblem' in (item.name or '').lower():
                print(f"Found Emblem on {c.nickname}:")
                if item.potential:
                    for opt in item.potential.values():
                        # opt is usually dict with 'label' or just a string
                        label = opt.get('label', opt) if isinstance(opt, dict) else opt
                        print(f"  POT: {label}")
                if item.bonus_potential:
                    for opt in item.bonus_potential.values():
                        label = opt.get('label', opt) if isinstance(opt, dict) else opt
                        print(f"  BPOT: {label}")
                print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test())
