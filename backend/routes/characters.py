from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional

from services.market_data import market_data_service
from services.cache import cache_get, cache_set
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/characters", tags=["Characters"])


@router.get("/")
async def list_characters(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    class_filter: str = Query("all_classes"),
    job_filter: str = Query("all_jobs"),
    level_min: int = Query(0, ge=0),
    level_max: int = Query(300, le=300),
):
    """List marketplace characters with filtering."""
    chars, is_last, total_count = await market_data_service.fetch_characters(
        page=page,
        page_size=page_size,
        class_filter=class_filter,
        level_min=level_min,
        level_max=level_max,
    )

    # Client-side job filtering (MSU API doesn't support it upstream)
    if job_filter and job_filter != "all_jobs":
        chars = [c for c in chars if c.job_name and job_filter.lower() in c.job_name.lower()]
        total_count = len(chars)

    # Enrich with fair value estimates using linear regression per class
    cache_key = "floor_prices_v3"
    cached = await cache_get(cache_key)
    listings = (cached or {}).get("listings", {}) if cached else {}
    buckets = (cached or {}).get("floor_prices", {}) if cached else {}

    # Pre-compute linear regression (price ~ level) for each class
    regressions: dict = {}
    for cls, char_list in listings.items():
        if not isinstance(char_list, list) or len(char_list) < 2:
            continue
        n = 0
        sum_x = 0.0
        sum_y = 0.0
        sum_xy = 0.0
        sum_x2 = 0.0
        for c in char_list:
            lv = c.get("level", 0)
            pr = c.get("price", 0)
            if pr <= 0 or lv <= 0:
                continue
            n += 1
            sum_x += lv
            sum_y += pr
            sum_xy += lv * pr
            sum_x2 += lv * lv
        if n >= 2:
            denom = n * sum_x2 - sum_x * sum_x
            if denom != 0:
                slope = (n * sum_xy - sum_x * sum_y) / denom
                intercept = (sum_y - slope * sum_x) / n
                regressions[cls] = {
                    "slope": slope,
                    "intercept": intercept,
                    "n": n,
                    "mean_price": sum_y / n,
                    "mean_level": sum_x / n,
                }

    def _get_fair(char):
        """
        Fair value = linear regression prediction (price ~ level) for class.
        Distinct from bucket-based VS FLOOR — uses all listings to model
        the price trend, not just the lowest price in a bracket.
        """
        cls = char.class_name
        lv = char.level

        reg = regressions.get(cls)
        if reg and reg["n"] >= 2:
            predicted = reg["intercept"] + reg["slope"] * lv
            mean_p = reg["mean_price"]
            predicted = max(predicted, mean_p * 0.3)
            predicted = min(predicted, mean_p * 3.0)
            if predicted > 0:
                return round(predicted, 2)

        raw = listings.get(cls, [])
        if raw:
            prices = sorted([x["price"] for x in raw if x.get("price", 0) > 0])
            if prices:
                return round(prices[len(prices) // 2], 2)

        return 0

    result = []
    for c in chars:
        d = c.model_dump()
        fair = _get_fair(c)
        d["fair_value_estimate"] = fair
        result.append(d)

    return {
        "characters": result,
        "page": page,
        "page_size": page_size,
        "count": total_count,
        "is_last_page": is_last,
    }


@router.get("/floor-prices")
async def floor_prices():
    """
    Current floor prices by class and level bracket, plus raw listings
    for fine-grained interpolation by level.
    """
    cache_key = "floor_prices_v3"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Fetch more pages for accurate floors
    all_chars = await market_data_service.fetch_all_characters(max_pages=6)

    thresholds = [65, 120, 140, 160, 200, 220, 230, 240]

    def get_bracket(lv: int) -> str:
        current = "0"
        for t in thresholds:
            if lv >= t:
                current = str(t)
            else:
                break
        return current

    groups: dict[str, dict[str, list[float]]] = {}
    # Per-character level+price data for interpolation
    listings_by_class: dict[str, list[dict]] = {}
    class_counts: dict[str, int] = {}

    for char in all_chars:
        if char.price <= 0:
            continue
        cls = char.class_name or "Unknown"
        bracket = get_bracket(char.level)

        class_counts[cls] = class_counts.get(cls, 0) + 1

        if cls not in groups:
            groups[cls] = {}
        if bracket not in groups[cls]:
            groups[cls][bracket] = []
        groups[cls][bracket].append(char.price)

        if cls not in listings_by_class:
            listings_by_class[cls] = []
        listings_by_class[cls].append({"level": char.level, "price": char.price})

    # Build enriched floor map
    floors: dict[str, dict[str, dict]] = {}
    for cls, brackets in groups.items():
        floors[cls] = {}
        for bracket, prices in brackets.items():
            sorted_prices = sorted(prices)
            n = len(sorted_prices)
            median = sorted_prices[n // 2]
            avg = sum(sorted_prices) / n

            floors[cls][bracket] = {
                "min_price": sorted_prices[0],
                "max_price": sorted_prices[-1],
                "median_price": round(median, 2),
                "avg_price": round(avg, 2),
                "price_range": round(sorted_prices[-1] - sorted_prices[0], 2),
                "sample_size": n,
            }

    result = {
        "floor_prices": floors,
        "listings": listings_by_class,
        "class_counts": class_counts,
        "sample_size": len(all_chars),
        "thresholds": thresholds
    }
    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_LONG)
    return result

@router.get("/search")
async def search_character(query: str = Query(..., min_length=2)):
    """Search for a character by nickname or exact token_id.
    IMPORTANT: This route must be defined BEFORE /{token_id}/detail
    to prevent FastAPI from greedily matching 'search' as a token_id."""
    # Direct token ID lookup
    if query.startswith("CHAR"):
        char = await market_data_service.fetch_character_detail(query)
        if char:
            return {"results": [{"token_id": char.token_id, "name": char.name, "level": char.level, "class_name": char.class_name, "image_url": char.image_url}]}
        return {"results": []}

    # Nickname search — scans both marketplace and global Navigator
    query_lower = query.lower()
    seen = set()
    results = []

    # 1. Search Navigator (Global)
    nav_results = await market_data_service.search_navigator_characters(query)
    for nr in nav_results:
        if nr["token_id"] not in seen:
            seen.add(nr["token_id"])
            results.append(nr)

    # 2. Scans currently listed characters (Marketplace)
    all_chars = await market_data_service.fetch_all_characters(max_pages=3)
    for c in all_chars:
        if query_lower in c.name.lower() and c.token_id not in seen:
            seen.add(c.token_id)
            results.append({
                "token_id": c.token_id,
                "name": c.name,
                "level": c.level,
                "class_name": c.class_name,
                "image_url": c.image_url,
            })
            
    return {"results": results[:30]}


@router.get("/{token_id}/detail")
async def character_detail(token_id: str):
    """Get full character detail with AP stats, equipment, and nesolet."""
    char = await market_data_service.fetch_character_detail(token_id)
    if not char:
        return {"error": "Character not found", "token_id": token_id}
        
    char_dict = char.model_dump()

    # Inject precise Combat Rating Upgrade (CP contribution) into each item
    # so the frontend Tooltip can display it dynamically instead of +0
    try:
        from services.combat_power_engine import combat_power_engine

        ap_stats = char_dict.get("ap_stats") or {}
        real_cp = 0
        if isinstance(ap_stats, dict):
            # Primary source: combat_power stat block
            cp_stat = ap_stats.get("combat_power") or {}
            if isinstance(cp_stat, dict):
                real_cp = int(cp_stat.get("total", 0) or 0)
            elif isinstance(cp_stat, (int, float)):
                real_cp = int(cp_stat)

            # Fallback: attackPower is sometimes a plain string in the raw apStat
            if real_cp == 0:
                attack_power_raw = ap_stats.get("attackPower") or ap_stats.get("attack_power")
                if attack_power_raw:
                    try:
                        real_cp = int(float(str(attack_power_raw)))
                    except (ValueError, TypeError):
                        pass

        analysis = combat_power_engine.analyze_all_equipment(
            ap_stats=ap_stats,
            equipped_items=char_dict.get("equipped_items", []),
            job_name=char_dict.get("job_name", ""),
            real_cp=real_cp,
        )

        if "items" in analysis:
            # Build two lookup maps: token_id (most precise) and slot (fallback).
            # We use slot-based addressing as a last resort; for accessories with
            # identical slot names (ring1/ring2 etc.) token_id is essential.
            tid_to_cp: dict = {}
            slot_to_cp: dict = {}  # last-write wins — used only as fallback
            for ai in analysis["items"]:
                cp_val = ai.get("cp_contribution", 0)
                if ai.get("token_id"):
                    tid_to_cp[str(ai["token_id"])] = cp_val
                slot_key = str(ai.get("slot", "")).lower()
                if slot_key:
                    slot_to_cp[slot_key] = cp_val

            total_cp = analysis.get("real_cp", 0)
            char_dict["char_cp"] = total_cp
            char_dict["char_att"] = analysis.get("total_att", 0)
            char_dict["char_matt"] = analysis.get("total_matt", 0)

            print(f"DEBUG CP: char_cp={total_cp}, items_analyzed={len(analysis['items'])}, "
                  f"real_cp={real_cp}, calc_cp={analysis.get('calculated_cp', 0)}")

            for equip in char_dict.get("equipped_items", []):
                tid = str(equip.get("token_id") or "")
                if tid and tid in tid_to_cp:
                    equip["cp_contribution"] = tid_to_cp[tid]
                else:
                    # Fallback to slot name matching
                    slot_key = str(equip.get("slot", "")).lower()
                    if slot_key in slot_to_cp:
                        equip["cp_contribution"] = slot_to_cp[slot_key]

    except Exception as e:
        import traceback
        print(f"Error enriching item CP contributions for character {token_id}: {e}")
        traceback.print_exc()

    return JSONResponse(
        content={"character": char_dict},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )
