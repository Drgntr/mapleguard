import sys
sys.path.append("C:\\Scripts\\Maple\\MapleGuard\\backend")
import asyncio
from backend.config import get_settings
from backend.services.market_data import market_data_service, CHAR_HEADERS

async def test():
    url = "https://msu.io/api/marketplace/characters/CHARd2jrpc9siees73fn5cl0"
    try:
        data = market_data_service._get(url, CHAR_HEADERS)
        import json
        with open("char_yeggg.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Marketplace API success")
    except Exception as e:
        print("Marketplace error:", e)
    
    url2 = "https://msu.io/api/navigator/msu-stats/characters/CHARd2jrpc9siees73fn5cl0"
    try:
        data2 = market_data_service._get(url2, CHAR_HEADERS)
        import json
        with open("char_yeggg_nav.json", "w") as f:
            json.dump(data2, f, indent=2)
        print("Navigator API success")
    except Exception as e:
        print("Navigator error:", e)

asyncio.run(test())
