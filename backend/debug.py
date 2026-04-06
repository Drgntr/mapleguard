import asyncio
import sys
import json
sys.path.append('.')
from services.market_data import market_data_service

async def main():
    results = await market_data_service.search_navigator_characters('Chupper')
    asset_key = results[0]['token_id']
    char = await market_data_service.fetch_navigator_character_detail(asset_key)
    with open('chupper_equipment.json', 'w') as f:
        json.dump([e.model_dump() for e in char.equipped_items], f, indent=2)
    print("Done")

if __name__ == '__main__':
    asyncio.run(main())
