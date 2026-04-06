from fastapi import APIRouter, Query
from typing import Optional
import asyncio

from services.sniper_scanner import sniper_scanner
from services.anomaly_detector import anomaly_detector
from services.market_data import market_data_service
from services.sentinel_live import live_sentinel
from services.sentinel_historical import historical_sentinel
from services.rarity_engine import rarity_engine
from services.cache import cache_get, cache_set
from models.market import AnomalyType
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/market", tags=["Market"])


@router.get("/overview")
async def market_overview():
    """High-level market statistics dashboard."""
    cache_key = "market:overview"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    items, _ = await market_data_service.fetch_items(page=1, page_size=135)
    chars, _, _ = await market_data_service.fetch_characters(page=1, page_size=135)
    consumables = await market_data_service.fetch_consumables()

    item_prices = [i.price for i in items if i.price > 0]
    char_prices = [c.price for c in chars if c.price > 0]

    sf_dist = {}
    for i in items:
        sf = str(i.starforce)
        sf_dist[sf] = sf_dist.get(sf, 0) + 1

    pot_dist = {}
    pot_labels = {0: "None", 1: "Rare", 2: "Epic", 3: "Unique", 4: "Legendary", 5: "Special", 6: "Mythic"}
    for i in items:
        label = pot_labels.get(i.potential_grade, "?")
        pot_dist[label] = pot_dist.get(label, 0) + 1

    class_dist = {}
    for c in chars:
        cls = c.class_name or "Unknown"
        class_dist[cls] = class_dist.get(cls, 0) + 1

    level_dist = {}
    for c in chars:
        bracket = f"{c.level - (c.level % 10)}-{c.level - (c.level % 10) + 9}"
        level_dist[bracket] = level_dist.get(bracket, 0) + 1

    # Merge anomaly stats from all sources
    live_stats = live_sentinel.get_stats()
    hist_stats = historical_sentinel.get_stats()
    total_alerts = live_stats["total_alerts"] + hist_stats["total_alerts"]

    result = {
        "total_listed_items": len(items),
        "total_listed_characters": len(chars),
        "total_consumables": len(consumables),
        "avg_item_price": round(sum(item_prices) / len(item_prices), 2) if item_prices else 0,
        "median_item_price": round(sorted(item_prices)[len(item_prices) // 2], 2) if item_prices else 0,
        "min_item_price": round(min(item_prices), 2) if item_prices else 0,
        "max_item_price": round(max(item_prices), 2) if item_prices else 0,
        "avg_character_price": round(sum(char_prices) / len(char_prices), 2) if char_prices else 0,
        "median_character_price": round(sorted(char_prices)[len(char_prices) // 2], 2) if char_prices else 0,
        "starforce_distribution": sf_dist,
        "potential_distribution": pot_dist,
        "class_distribution": class_dist,
        "level_distribution": level_dist,
        "anomaly_stats": {
            "total_alerts": total_alerts,
            "live": live_stats,
            "historical": hist_stats,
        },
        "top_consumables": [
            {"name": c.name, "price": c.price, "volume": c.volume, "change": c.price_change}
            for c in sorted(consumables, key=lambda x: x.volume, reverse=True)[:10]
        ],
    }

    # ── Sniper Activity ──
    try:
        sniper_stats = sniper_scanner.get_stats()
        result["sniper_activity"] = {
            "total_snipes": sniper_stats.get("total_snipes", 0),
            "running": sniper_stats.get("running", False),
            "last_block": sniper_stats.get("last_block", 0),
            "enriched": sniper_stats.get("enriched", 0),
        }
    except Exception:
        result["sniper_activity"] = {"total_snipes": 0, "running": False, "last_block": 0, "enriched": 0}

    # ── Whale Highlight ──
    try:
        from services.whale_tracker import whale_tracker
        wb = whale_tracker.get_leaderboards()
        spenders = wb.get("top_spenders", [])
        earners = wb.get("top_earners", [])
        if spenders:
            result["whale_highlight"] = {
                "top_spender": spenders[0],
                "top_earner": earners[0] if earners else None,
            }
    except Exception:
        pass

    # ── Top CP Highlight ──
    try:
        from services.whale_tracker import whale_tracker
        wb = whale_tracker.get_leaderboards()
        cps = wb.get("top_cp", {})
        highest_cp_char = None
        for cls, chars in cps.items():
            if chars:
                top = chars[0]
                if highest_cp_char is None or top["cp"] > highest_cp_char["cp"]:
                    highest_cp_char = top
        if highest_cp_char:
            result["top_cp_highlight"] = highest_cp_char
    except Exception:
        pass

    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_SECONDS)
    return result


@router.get("/anomalies")
async def get_anomalies(
    severity: Optional[str] = Query(None),
    anomaly_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Merged anomalies from live + historical sentinels."""
    live_alerts = live_sentinel.get_alerts(severity, anomaly_type, limit)
    hist_alerts = historical_sentinel.get_alerts(severity, anomaly_type, limit)

    all_alerts = live_alerts + hist_alerts
    all_alerts.sort(key=lambda a: a.get("detected_at", ""), reverse=True)
    all_alerts = all_alerts[:limit]

    return {
        "anomalies": all_alerts,
        "count": len(all_alerts),
        "stats": {
            "live": live_sentinel.get_stats(),
            "historical": historical_sentinel.get_stats(),
        },
    }


@router.get("/scarcity-ranking")
async def scarcity_ranking(
    limit: int = Query(50, ge=1, le=200),
):
    """Items ranked by scarcity score."""
    cache_key = f"scarcity_ranking:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    items = await market_data_service.fetch_all_items(max_pages=3)
    rarity_engine.rebuild_index(items)

    scored = []
    for item in items:
        score = rarity_engine.compute_score(item)
        scored.append({
            **score.model_dump(),
            "price": item.price,
            "image_url": item.image_url,
            "starforce": item.starforce,
            "potential_grade": item.potential_grade,
            "category_label": item.category_label,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    result = {"ranking": scored[:limit], "total_scored": len(scored)}
    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_LONG)
    return result


# ─── Live Sentinel Endpoints ────────────────────────────────────────

@router.get("/sentinel/live/stats")
async def get_live_sentinel_stats():
    """Live sentinel scanning status and metrics."""
    return live_sentinel.get_stats()


@router.get("/sentinel/live/alerts")
async def get_live_sentinel_alerts(
    severity: Optional[str] = Query(None),
    anomaly_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Recent anomalies caught by the real-time scanner."""
    return {
        "alerts": live_sentinel.get_alerts(severity, anomaly_type, limit),
        "stats": live_sentinel.get_stats(),
    }


# ─── Historical Sentinel Endpoints ──────────────────────────────────

@router.post("/sentinel/historical/scan")
async def trigger_historical_scan():
    """Trigger a deep historical anomaly scan in the background."""
    if historical_sentinel._scanning:
        return {"status": "already_running", "message": "A scan is already in progress"}
    asyncio.create_task(historical_sentinel.run_full_scan())
    return {"status": "started", "message": "Historical deep scan running in background"}


@router.get("/sentinel/historical/analysis")
async def get_historical_analysis():
    """Get the latest deep market analysis results."""
    analysis = historical_sentinel.get_analysis()
    if not analysis:
        return {"status": "no_data", "message": "No historical scan has been completed yet. Wait for the first scan or POST /sentinel/historical/scan."}
    return analysis


@router.get("/sentinel/historical/alerts")
async def get_historical_alerts(
    severity: Optional[str] = Query(None),
    anomaly_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Anomalies found in historical data analysis."""
    return {
        "alerts": historical_sentinel.get_alerts(severity, anomaly_type, limit),
        "stats": historical_sentinel.get_stats(),
    }


@router.get("/sentinel/historical/stats")
async def get_historical_stats():
    """Historical sentinel status."""
    return historical_sentinel.get_stats()


@router.get("/sentinel/snipes")
async def get_past_snipes():
    """Returns confirmed historical bot snipes from the DB."""
    snipes = await historical_sentinel.get_historical_bot_snipes(limit=500)
    return {"snipes": snipes, "count": len(snipes)}


@router.get("/sentinel/snipes/static")
async def get_static_snipes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    filter_type: Optional[str] = Query(None),
):
    """Paginated access to scanner-generated snipe data (from scanner_state.json)."""
    import json as _json
    import os as _os

    state_file = _os.path.join(
        _os.path.dirname(_os.path.dirname(__file__)),
        "scripts", "scanner_state.json",
    )

    cache_key = "static_snipes_data"
    cached = await cache_get(cache_key)

    if cached:
        all_snipes = cached
    else:
        if not _os.path.exists(state_file):
            return {"snipes": [], "total": 0, "page": page, "pages": 0}
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = _json.load(f)
            all_snipes = state.get("snipes", [])
            await cache_set(cache_key, all_snipes, ttl=300)
        except Exception:
            return {"snipes": [], "total": 0, "page": page, "pages": 0}

    # Filter out non-character entries with floor_price < 150000 NESO
    # Old records have type "Sale" (unenriched) so we can't rely on type == "item"
    filtered = [
        s for s in all_snipes
        if s.get("type", "").lower() == "character"
        or (s.get("floor_price") or 0) >= 150000
    ]

    # Type filter
    if filter_type and filter_type != "all":
        filtered = [
            s for s in filtered
            if s.get("type", "").lower() == filter_type.lower()
        ]

    total = len(filtered)
    pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    page_data = filtered[start : start + page_size]

    return {
        "snipes": page_data,
        "total": total,
        "page": page,
        "pages": pages,
        "page_size": page_size,
    }


# ─── Sniper Wallet Ranking ───────────────────────────────────────────

@router.get("/sentinel/sniper-ranking")
async def get_sniper_ranking(
    limit: int = Query(50, ge=1, le=200),
):
    """Rank wallets by number of snipes across all history."""
    import json as _json
    import os as _os
    from collections import defaultdict

    cache_key = f"sniper_ranking:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    state_file = _os.path.join(
        _os.path.dirname(_os.path.dirname(__file__)),
        "scripts", "scanner_state.json",
    )
    if not _os.path.exists(state_file):
        return {"ranking": [], "total_wallets": 0}

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = _json.load(f)
        all_snipes = state.get("snipes", [])
    except Exception:
        return {"ranking": [], "total_wallets": 0}

    # Filter same as static endpoint (no low floor items)
    valid = [
        s for s in all_snipes
        if s.get("type", "").lower() == "character"
        or (s.get("floor_price") or 0) >= 150000
    ]

    wallet_stats: dict = defaultdict(lambda: {
        "address": "",
        "total_snipes": 0,
        "total_spent": 0.0,
        "total_floor_value": 0.0,
        "total_saved": 0.0,
        "types": defaultdict(int),
        "first_seen": "",
        "last_seen": "",
    })

    for s in valid:
        buyer = s.get("buyer", "")
        if not buyer:
            continue
        w = wallet_stats[buyer]
        w["address"] = buyer
        w["total_snipes"] += 1
        w["total_spent"] += s.get("price", 0)
        floor = s.get("floor_price", 0) or 0
        w["total_floor_value"] += floor
        w["total_saved"] += max(0, floor - s.get("price", 0))
        t = s.get("type", "Sale")
        w["types"][t] += 1
        dt = s.get("date", "")
        if dt:
            if not w["first_seen"] or dt < w["first_seen"]:
                w["first_seen"] = dt
            if not w["last_seen"] or dt > w["last_seen"]:
                w["last_seen"] = dt

    ranking = sorted(wallet_stats.values(), key=lambda x: x["total_snipes"], reverse=True)
    # Convert defaultdict types to regular dict
    for w in ranking:
        w["types"] = dict(w["types"])

    result = {
        "ranking": ranking[:limit],
        "total_wallets": len(ranking),
        "total_snipes_analyzed": len(valid),
    }
    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_LONG)
    return result


# ─── Sniper Scanner ──────────────────────────────────────────────────

@router.get("/sentinel/scanner/stats")
async def get_scanner_stats():
    """Background sniper scanner status."""
    try:
        from services.sniper_scanner import sniper_scanner
        return sniper_scanner.get_stats()
    except Exception:
        return {"running": False, "error": "Scanner not available"}


# ─── Whale Tracker ───────────────────────────────────────────────────

@router.get("/whales/leaderboards")
async def get_whale_leaderboards():
    """Top spenders, earners, farmers, and CP leaders."""
    try:
        from services.whale_tracker import whale_tracker
        return whale_tracker.get_leaderboards()
    except Exception:
        return {"top_spenders": [], "top_earners": [], "top_farmers": [], "top_cp": {}}


# ─── Blockchain Indexer ─────────────────────────────────────────────

@router.get("/indexer/stats")
async def get_indexer_stats():
    """Blockchain indexer status and statistics."""
    try:
        from services.blockchain_indexer import blockchain_indexer
        return blockchain_indexer.get_stats()
    except Exception:
        return {"error": "Indexer unavailable"}


@router.get("/indexer/recent-matches")
async def get_recent_matches(limit: int = 50):
    """Recent OrderMatched events from the blockchain."""
    try:
        from services.blockchain_indexer import blockchain_indexer
        return {"matches": blockchain_indexer.get_recent_matches(limit)}
    except Exception:
        return {"matches": []}


@router.get("/indexer/recent-transfers")
async def get_recent_transfers(limit: int = 50):
    """Recent NFT transfers from the blockchain."""
    try:
        from services.blockchain_indexer import blockchain_indexer
        return {"transfers": blockchain_indexer.get_recent_transfers(limit)}
    except Exception:
        return {"transfers": []}
