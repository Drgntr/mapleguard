import sys
import json
import traceback

sys.path.append(r"c:\Scripts\Maple\MapleGuard\backend")
from services.market_data import market_data_service

import asyncio

async def test_api():
    output = []
    
    # Let's test just what market_data_service is doing for Warrior
    class_filter = "Warrior"
    
    url = "https://api.msu.io/marketplace/explore/characters"
    body = {
        "filter": {
            "price": {"min": 0, "max": 10000000000},
            "level": {"min": 0, "max": 300},
            "class": class_filter
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

    try:
        raw_data = market_data_service._post(url, body, char_headers)
        output.append("Success fetching raw data")
        
        # Now let's try to parse
        from models.character import CharacterListing
        raw_chars = raw_data.get("characters", [])
        
        output.append(f"Got {len(raw_chars)} raw characters")
        if raw_chars:
            output.append("First char raw: " + json.dumps(raw_chars[0]))
            
            try:
                char = CharacterListing.from_explore_api(raw_chars[0])
                output.append("Parsed successfully: " + char.name)
            except Exception as e:
                output.append("Pydantic Error on first char: " + traceback.format_exc())
                
    except Exception as e:
        output.append("Network Error: " + traceback.format_exc())

    with open("debug_out.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

asyncio.run(test_api())
