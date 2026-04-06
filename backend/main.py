import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from db.database import init_db
from routes import items, characters, market, calculator, leaderboard
from services.market_data import market_data_service

# ── Optional long-running services ───────────────────────────────────
_enable_services = os.environ.get("ENABLE_SERVICES", "true").lower() == "true"

if _enable_services:
    from services.sentinel_live import live_sentinel
    from services.sentinel_historical import historical_sentinel
    from services.sniper_scanner import sniper_scanner
    from services.blockchain_indexer import blockchain_indexer
    from services.leaderboard_manager import (
        scan_all_task, enrich_chars_task, enrich_items_task,
        watch_chars_task, watch_items_task,
    )

    try:
        from services.whale_tracker import whale_tracker
    except Exception:
        whale_tracker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()

    tasks = []

    if _enable_services:
        # Core services
        tasks.append(asyncio.create_task(live_sentinel.run_loop(interval=15)))
        tasks.append(asyncio.create_task(historical_sentinel.run_loop(interval=600)))
        tasks.append(asyncio.create_task(sniper_scanner.run()))
        tasks.append(asyncio.create_task(blockchain_indexer.run_full_index(start_block=12_000_000)))

        if whale_tracker:
            tasks.append(asyncio.create_task(whale_tracker.run_loop(interval=60)))

        # ── Leaderboard Backend ─────────────────────────────────────
        tasks.append(asyncio.create_task(scan_all_task()))
        tasks.append(asyncio.create_task(enrich_chars_task()))
        tasks.append(asyncio.create_task(enrich_items_task()))
        tasks.append(asyncio.create_task(watch_chars_task()))
        tasks.append(asyncio.create_task(watch_items_task()))
        # ─────────────────────────────────────────────────────────────

    yield

    # Shutdown
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await market_data_service.close()


app = FastAPI(
    title="MapleGuard & Market Sentinel",
    description="Market intelligence platform for MapleStory Universe on Henesys",
    version="1.0.0",
    lifespan=lifespan,
)

# ALLOW ANY origin for development + Vercel deployments + Railway
# In production, restrict to specific origins
FRONTEND_ORIGINS = os.environ.get("FRONTEND_ORIGINS", "").strip()
if FRONTEND_ORIGINS:
    origins = [o.strip() for o in FRONTEND_ORIGINS.split(",") if o.strip()]
else:
    origins = ["*"]  # Allow all origins (Vercel + localhost)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router)
app.include_router(characters.router)
app.include_router(leaderboard.router)
app.include_router(market.router)
app.include_router(calculator.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "MapleGuard"}
