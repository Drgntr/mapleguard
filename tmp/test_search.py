import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from services.market_data import market_data_service

async def test_search():
    query = "Shiki"
    print(f"Searching for '{query}'...")
    results = await market_data_service.search_navigator_characters(query)
    print(f"Navigator results: {len(results)}")
    for r in results:
        print(f" - {r['name']} ({r['token_id']})")
    
    # Test full search route logic
    from routes.characters import search_character
    # We need to mock the Query object or just call the logic
    # Let's just manually run the merge logic here
    seen = set()
    final_results = []
    for nr in results:
        if nr["token_id"] not in seen:
            seen.add(nr["token_id"])
            final_results.append(nr)
    
    print(f"Final merged results: {len(final_results)}")

if __name__ == "__main__":
    asyncio.run(test_search())
