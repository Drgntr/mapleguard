import asyncio
import sys
import json
sys.path.append('.')
from services.market_data import market_data_service

async def main():
    results = await market_data_service.search_navigator_characters('Chupper')
    asset_key = results[0]['token_id']
    info_url = f"https://msu.io/navigator/api/navigator/characters/{asset_key}/info"
    equip_url = f"https://msu.io/navigator/api/navigator/characters/{asset_key}/equip-preset"
    hyper_url = f"https://msu.io/navigator/api/navigator/characters/{asset_key}/hyper-stat"

    info = market_data_service._get(info_url)
    equip = market_data_service._get(equip_url)
    try:
        hyper = market_data_service._get(hyper_url)
    except Exception as e:
        hyper = {"error": str(e)}

    with open('chupper_api_dump.json', 'w') as f:
        json.dump({"info": info, "equip": equip, "hyper": hyper}, f, indent=2)
    print("Dump completed")

if __name__ == '__main__':
    asyncio.run(main())
