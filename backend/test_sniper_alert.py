import asyncio
import time
from db.database import async_session, OrderMatchDB, init_db

async def inject_fake_snipes():
    await init_db()
    async with async_session() as db:
        # Fake Sniper 1 (1 NESO Dump)
        fake_1 = OrderMatchDB(
            tx_hash=f"0xfake_sniper_tx_{int(time.time())}_1",
            block_number=9999991,
            maker="0xPoorVictim1",
            taker="0xSniperBot99",
            token_address="0xItemContract",
            token_id="999999999", 
            price_wei="1000000000000000000" # 1 NESO
        )
        # Fake Sniper 2 (Wrong Price Character Snipe - e.g 15000 NESO)
        fake_2 = OrderMatchDB(
            tx_hash=f"0xfake_sniper_tx_{int(time.time())}_2",
            block_number=9999992,
            maker="0xBotFarmOffload",
            taker="0xSniperBot99",
            token_address="0xCharContract",
            token_id="8253328733902951591054595041026", # Real character ID format
            price_wei="15000000000000000000000" # 15k NESO
        )
        
        db.add(fake_1)
        db.add(fake_2)
        await db.commit()
        print("Successfully injected 2 sniper transactions for Sentinel detection!")

if __name__ == "__main__":
    asyncio.run(inject_fake_snipes())
