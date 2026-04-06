from fastapi import APIRouter, Query
from typing import Optional
import asyncio
import os

from services.leaderboard_db_service import leaderboard_db_service
from services.cache import cache_get, cache_set

try:
    from config import get_settings
    settings = get_settings()
except ImportError:
    class _FakeSettings:
        CACHE_TTL_LONG = 300
    settings = _FakeSettings()

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])

# Threshold for "has data" check — below this, fallback to old live API service
DB_MIN_THRESHOLD = 10


async def _has_db_data() -> bool:
    """Check if the DB has enough enriched characters to serve leaderboards."""
    try:
        stats = await leaderboard_db_service.get_stats()
        char_count = stats.get("characters", {}).get("enriched", 0)
        return char_count >= DB_MIN_THRESHOLD
    except Exception:
        return False


@router.get("/scan")
async def leaderboard_scan(limit: int = Query(50, ge=1, le=200)):
    """
    Full CP leaderboard: DB-first, with legacy API fallback.
    """
    cache_key = f"leaderboard:scan:v4:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    has_data = await _has_db_data()
    if has_data:
        result = await leaderboard_db_service.get_combined_leaderboard(limit=limit)
    else:
        # Fallback to old API-based service
        from services.market_data import market_data_service
        from services.openapi_service import openapi_service
        from services.leaderboard_service import leaderboard_service
        result = await leaderboard_service.compute_combined(limit=limit)

    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_LONG)
    return result


@router.get("/combined")
async def combined_leaderboard(limit: int = Query(100, ge=1, le=200)):
    """Top CP characters across all classes."""
    return await leaderboard_db_service.get_combined_leaderboard(limit=limit)


@router.get("/by-class")
async def leaderboard_by_class(
    class_name: Optional[str] = Query(None, description="Filter by specific class. Omit for all classes."),
    limit: int = Query(50, ge=1, le=200),
):
    """Leaderboard grouped by class."""
    return await leaderboard_db_service.get_cp_leaderboard(class_name=class_name, limit=limit)


@router.get("/cp-overview")
async def cp_overview():
    """Quick CP summary: top 3 per class with stats."""
    cache_key = "leaderboard:cp_overview:v2"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    has_data = await _has_db_data()
    if has_data:
        # Build from DB
        classes_data = await leaderboard_db_service.get_classes()
        result = {
            "classes": {
                c["class_name"]: {
                    "character_count": c["count"],
                    "highest_cp": c["max_cp"],
                }
                for c in classes_data[:20]
            },
            "total_classes": len(classes_data),
            "backend": "database",
        }
    else:
        # Fallback
        from services.leaderboard_service import leaderboard_service
        result = await leaderboard_service.compute_by_class(limit=20)
        result["backend"] = "api_fallback"

    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_LONG)
    return result


# ── New DB-backed endpoints ────────────────────────────────────────

@router.get("/stats")
async def leaderboard_stats():
    """Dashboard stats: totals, enrichment state, class distribution."""
    return await leaderboard_db_service.get_stats()


@router.get("/characters/{token_id}")
async def character_detail(token_id: str):
    """Full character snapshot detail from DB."""
    detail = await leaderboard_db_service.get_char_detail(token_id)
    if not detail:
        return {"error": "Character not found in database", "token_id": token_id}
    return detail


@router.get("/items/{token_id}")
async def item_detail(token_id: str):
    """Full item snapshot detail from DB."""
    detail = await leaderboard_db_service.get_item_detail(token_id)
    if not detail:
        return {"error": "Item not found in database", "token_id": token_id}
    return detail


@router.get("/recent-mints")
async def recent_mints(
    nft_type: Optional[str] = Query(None, description="Filter by 'character' or 'item'"),
    limit: int = Query(50, ge=1, le=200),
):
    """Recent mint events."""
    return await leaderboard_db_service.get_recent_mints(nft_type=nft_type, limit=limit)


@router.get("/classes")
async def list_classes():
    """All known classes with character counts and max CP."""
    return await leaderboard_db_service.get_classes()


@router.get("/characters/search")
async def search_characters(
    q: str = Query(..., min_length=1, description="Search query (name, class, or job)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search characters by name or class."""
    return await leaderboard_db_service.search_characters(query=q, limit=limit)


# ── Wallet leaderboards (unchanged — still uses whale tracker) ─────

@router.get("/wallets/spenders")
async def top_spenders(limit: int = Query(20, ge=1, le=100)):
    """Top wallets by NESO spent (from blockchain indexer)."""
    try:
        from services.whale_tracker import whale_tracker
        data = whale_tracker.get_leaderboards()
        return {"spenders": data["top_spenders"][:limit]}
    except Exception:
        return {"spenders": []}


@router.get("/wallets/earners")
async def top_earners(limit: int = Query(20, ge=1, le=100)):
    """Top wallets by NESO earned (from blockchain indexer)."""
    try:
        from services.whale_tracker import whale_tracker
        data = whale_tracker.get_leaderboards()
        return {"earners": data["top_earners"][:limit]}
    except Exception:
        return {"earners": []}


@router.get("/wallets/farmers")
async def top_farmers(limit: int = Query(20, ge=1, le=100)):
    """Top bot farmer wallets (from blockchain transfer analysis)."""
    try:
        from services.whale_tracker import whale_tracker
        data = whale_tracker.get_leaderboards()
        return {"farmers": data["top_farmers"][:limit]}
    except Exception:
        return {"farmers": []}


# ── Job leaderboards ──────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs():
    """All known jobs with character counts and max CP."""
    return await leaderboard_db_service.list_jobs()


@router.get("/job")
async def job_leaderboard(limit: int = Query(100, ge=1, le=200)):
    """Combined leaderboard across all jobs."""
    return await leaderboard_db_service.get_job_leaderboard(limit=limit)


@router.get("/job/{job_name}")
async def job_leaderboard_by_name(
    job_name: str,
    limit: int = Query(100, ge=1, le=200),
):
    """Top 10 highlighted + full list up to limit for a specific job."""
    return await leaderboard_db_service.get_job_leaderboard(job_name=job_name, limit=limit)


@router.post("/reset-enrich")
async def reset_enrichment():
    return await leaderboard_db_service.reset_enrichment()
