import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from db.database import init_db
from routes import items, characters, market, calculator, leaderboard
from services.market_data import market_data_service

# ── Optional long-running services ───────────────────────────────────
# Disabled by default — enable via ENABLE_SERVICES=true env var
_enable_services = os.environ.get("ENABLE_SERVICES", "false").lower() == "true"
print(f"[START] ENABLE_SERVICES={_enable_services}")

if _enable_services:
    from services.leaderboard_manager import (
        scan_all_task, enrich_chars_task, watch_chars_task,
    )
    print("[START] Leaderboard services imported OK")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()

    tasks = []

    if _enable_services:
        from services.leaderboard_manager import re_enrich_task
        print("[START] Launching leaderboard pipeline...")
        tasks.append(asyncio.create_task(scan_all_task()))
        tasks.append(asyncio.create_task(enrich_chars_task(batch_size=5)))
        tasks.append(asyncio.create_task(watch_chars_task()))
        tasks.append(asyncio.create_task(re_enrich_task()))
        print("[START] All leaderboard tasks launched!")

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
