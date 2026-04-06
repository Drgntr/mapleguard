import asyncio
import os
import sys
import json
from services.market_data import MarketDataService

async def main():
    token_id = "CHAR-554471018318855681-7" # Chupper
    service = MarketDataService()
    char = await service.fetch_character_detail(token_id)
    if not char:
        print("Character NOT found")
        return
    
    print(f"Character: {char.name}, Level: {char.level}")
    if char.equipped_items:
        first = char.equipped_items[0]
        print(f"First Item: {first.name}, Type: {first.item_type}")
        print("Stats Keys:", first.stats.keys())
        # Print a few attributes if they exist
        if "attributes" in first.stats:
             print("Attributes sample:", first.stats["attributes"][:3])
        else:
             print("Full stats node:", json.dumps(first.stats, indent=2)[:500])
             
if __name__ == "__main__":
    asyncio.run(main())
