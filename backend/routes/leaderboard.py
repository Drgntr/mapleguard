from fastapi import APIRouter, Query
from typing import Optional

from services.leaderboard_db_service import leaderboard_db_service

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])

@router.get("/combined")
async def combined_leaderboard(
    limit: int = Query(100, ge=1, le=200),
    page: int = Query(1, ge=1),
):
    """Top CP characters across all classes with pagination."""
    offset = (page - 1) * limit
    return await leaderboard_db_service.get_combined_leaderboard(limit=limit, offset=offset, page=page)


# ── DB-backed endpoints ─────────────────────────────────────────────────

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
async def job_leaderboard(
    job: str = Query(None, description="Filter by job name"),
    limit: int = Query(100, ge=1, le=200),
):
    """Job leaderboard. No filter = all jobs. Use ?job=JobName to filter.

    Uses query param instead of path param to handle special characters
    in job names (e.g. 'Ice/Lightning', 'Battle Mage').
    """
    return await leaderboard_db_service.get_job_leaderboard(job_name=job, limit=limit)


# ── Enrichment stats ──────────────────────────────────────────────────

@router.get("/enrich-stats")
async def enrichment_stats():
    """Enrichment pipeline statistics: success rate, errors, batches."""
    from services.leaderboard_manager import get_enrich_stats
    return get_enrich_stats()
