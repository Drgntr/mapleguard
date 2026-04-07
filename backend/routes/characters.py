import json
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from typing import Optional

from services.market_data import market_data_service
from services.cache import cache_get, cache_set
from db.database import async_session, CharacterMarketStatus, CharacterSaleHistory
from config import get_settings


def json_loads(val):
    if val is None:
        return []
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return []
    return val


settings = get_settings()
router = APIRouter(prefix="/api/characters", tags=["Characters"])


# Level thresholds for floor pricing — buckets of 10 (e.g. 130→131-139, 140→141-149)
FLOOR_THRESHOLDS = [65, 75, 85, 95, 105, 115, 125, 135, 145, 155, 165, 175, 185, 195, 200, 210, 220, 230, 240]


async def _get_class_level_median(cls: str, level: int) -> Optional[float]:
    """Get median price for same class in same level bracket."""
    current = "0"
    for t in FLOOR_THRESHOLDS:
        if level >= t:
            current = str(t)
        else:
            break

    # Use the same floor_prices logic to get bracket median
    try:
        all_chars = await market_data_service.fetch_all_characters(max_pages=3)
        prices = [c.price for c in all_chars if c.price > 0 and c.class_name == cls]
        if not prices:
            return None
        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        return prices_sorted[n // 2]
    except Exception:
        return None


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

    # Enrich with fair value from DB (computed by char_fair_value engine)
    enriched_map: dict[str, dict] = {}
    try:
        async with async_session() as session:
            stmt = select(CharacterMarketStatus).where(
                CharacterMarketStatus.status.in_(["enriched", "pending"])
            )
            rows = (await session.execute(stmt)).scalars().all()
            for r in rows:
                enriched_map[r.token_id] = {
                    "fair_value": r.fair_value,
                    "confidence": r.confidence,
                    "arcane_tier": r.arcane_set_tier,
                    "ability_total": r.ability_total,
                    "gear_score": r.gear_score,
                }
    except Exception:
        pass  # DB not ready or no enriched data yet

    # Compute median price per class + level bracket from current listings for fallback
    class_bracket_medians: dict[str, dict[str, float]] = {}
    for c in chars:
        if c.price <= 0:
            continue
        cls = c.class_name
        # Determine level bracket
        bracket = "0"
        for t in FLOOR_THRESHOLDS:
            if c.level >= t:
                bracket = str(t)
            else:
                break
        if cls not in class_bracket_medians:
            class_bracket_medians[cls] = {}
        if bracket not in class_bracket_medians[cls]:
            class_bracket_medians[cls][bracket] = []
        class_bracket_medians[cls][bracket].append(c.price)
    for cls in class_bracket_medians:
        for bracket in class_bracket_medians[cls]:
            prices = sorted(class_bracket_medians[cls][bracket])
            class_bracket_medians[cls][bracket] = prices[len(prices) // 2]

    def _get_level_bracket(level: int) -> str:
        bracket = "0"
        for t in FLOOR_THRESHOLDS:
            if level >= t:
                bracket = str(t)
            else:
                break
        return bracket

    def _get_fair_fallback(char):
        """Fallback: median price for same class and level bracket (not entire class)."""
        bracket = _get_level_bracket(char.level)
        if char.class_name in class_bracket_medians:
            return class_bracket_medians[char.class_name].get(bracket, 0)
        return 0

    result = []
    for c in chars:
        d = c.model_dump()

        # Try enriched fair value first (from DB engine)
        if c.token_id in enriched_map:
            ev = enriched_map[c.token_id]
            d["fair_value_estimate"] = ev["fair_value"]
            d["fair_confidence"] = ev["confidence"]
            d["arcane_tier"] = ev["arcane_tier"]
            d["ability_total"] = ev["ability_total"]
            d["is_enriched"] = True
        else:
            # <200 chars: show level-based floor estimate
            # 200+ chars: show 0 (need enrichment - arcane/gear/value unknown without V-skill data)
            if c.level < 200:
                fallback = _get_fair_fallback(c)
                d["fair_value_estimate"] = fallback
                d["fair_confidence"] = "floor_estimate"
                d["is_enriched"] = False
            else:
                d["fair_value_estimate"] = 0
                d["fair_confidence"] = "pending_enrich"
                d["is_enriched"] = False
            d["arcane_tier"] = "none" if c.level < 200 else "unknown"
            d["ability_total"] = 0

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

    def get_bracket(lv: int) -> str:
        current = "0"
        for t in FLOOR_THRESHOLDS:
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
        "thresholds": FLOOR_THRESHOLDS
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


@router.get("/enriched-listings")
async def enriched_listings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort: str = Query("fair_vs_price"),
    class_filter: str = Query(""),
    status_filter: str = Query("enriched"),
):
    """Paginated enriched listings with fair value.
    When status_filter='enriched', returns only enriched listings.
    When status_filter='', returns ALL listings (enriched + unenriched)."""
    async with async_session() as session:
        filters = []
        if class_filter and class_filter != "all_classes":
            filters.append(CharacterMarketStatus.class_name == class_filter)

        # Allow viewing all listings including pending/unenriched
        if status_filter:
            statuses = status_filter.split(",")
            filters.append(CharacterMarketStatus.status.in_(statuses))

        count_stmt = select(func.count(CharacterMarketStatus.token_id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await session.execute(count_stmt)).scalar_one()

        # Build query with sorting
        stmt = select(CharacterMarketStatus)
        if filters:
            stmt = stmt.where(*filters)

        if sort == "fair_vs_price":
            # Cheapest relative to fair value first
            from sqlalchemy import case
            stmt = stmt.where(
                CharacterMarketStatus.fair_value > 0,
                CharacterMarketStatus.price > 0,
            ).order_by(
                (CharacterMarketStatus.price / CharacterMarketStatus.fair_value).asc()
            )
        elif sort == "price_asc":
            stmt = stmt.order_by(CharacterMarketStatus.price.asc())
        elif sort == "price_desc":
            stmt = stmt.order_by(CharacterMarketStatus.price.desc())
        elif sort == "level_asc":
            stmt = stmt.order_by(CharacterMarketStatus.level.asc())
        elif sort == "level_desc":
            stmt = stmt.order_by(CharacterMarketStatus.level.desc())
        elif sort == "gear_desc":
            stmt = stmt.order_by(CharacterMarketStatus.gear_score.desc())
        else:
            stmt = stmt.order_by(CharacterMarketStatus.scanned_at.desc())

        offset = (page - 1) * page_size
        stmt = stmt.limit(page_size).offset(offset)
        rows = (await session.execute(stmt)).scalars().all()

    result = []
    for r in rows:
        d = {
            "token_id": r.token_id,
            "asset_key": r.asset_key,
            "name": r.name,
            "class_name": r.class_name,
            "job_name": r.job_name,
            "level": r.level,
            "price": r.price,
            "arcane_force": r.arcane_force,
            "arcane_set_tier": r.arcane_set_tier,
            "ability_grades": json_loads(r.ability_grades),
            "ability_total": r.ability_total,
            "weapon_starforce": r.weapon_starforce,
            "weapon_potential_grade": r.weapon_potential_grade,
            "gear_score": r.gear_score,
            "fair_value": r.fair_value,
            "fair_breakdown": json_loads(r.fair_breakdown) if r.fair_breakdown else {},
            "confidence": r.confidence,
            "status": r.status,
            "price_change_pct": r.price_change_pct,
            "listed_at": str(r.listed_at) if r.listed_at else None,
        }
        if r.fair_value > 0 and r.price > 0:
            d["fair_vs_floor"] = round((r.price - r.fair_value) / r.fair_value * 100, 2)
        else:
            d["fair_vs_floor"] = None
        result.append(d)

    return {
        "listings": result,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/enriched/{token_id}")
async def enriched_detail(token_id: str):
    """Single enriched listing detail with full fair breakdown."""
    async with async_session() as session:
        stmt = select(CharacterMarketStatus).where(
            CharacterMarketStatus.token_id == token_id
        )
        row = (await session.execute(stmt)).scalar_one_or_none()

    if not row:
        return {"error": "Not found", "token_id": token_id}

    breakdown = {}
    if row.fair_breakdown:
        breakdown = json_loads(row.fair_breakdown)

    return {
        "level": row.level,
        "price": row.price,
        "arcane_force": row.arcane_force,
        "arcane_set_tier": row.arcane_set_tier,
        "ability_grades": json_loads(row.ability_grades),
        "ability_total": row.ability_total,
        "weapon_starforce": row.weapon_starforce,
        "weapon_potential_grade": row.weapon_potential_grade,
        "gear_score": row.gear_score,
        "equipped_items": json_loads(row.equipped_item_ids_json) if row.equipped_item_ids_json else [],
        "fair_value": row.fair_value,
        "fair_breakdown": breakdown,
        "confidence": row.confidence,
        "status": row.status,
        "price_change_pct": row.price_change_pct,
        "listed_at": str(row.listed_at) if row.listed_at else None,
    }


@router.get("/recent-sales")
async def recent_sales(
    limit: int = Query(50, ge=1, le=200),
    class_filter: str = Query(""),
):
    """Recent character sales with enriched snapshots."""
    async with async_session() as session:
        stmt = select(CharacterSaleHistory).order_by(
            CharacterSaleHistory.sale_date.desc()
        ).limit(limit)
        if class_filter and class_filter != "all_classes":
            stmt = stmt.where(CharacterSaleHistory.class_name == class_filter)
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "sales": [
            {
                "tx_hash": r.tx_hash,
                "buyer": r.buyer,
                "seller": r.seller,
                "price": r.price,
                "sale_date": str(r.sale_date),
                "token_id": r.token_id,
                "class_name": r.class_name,
                "level": r.level,
                "arcane_force": r.arcane_force,
                "ability_total": r.ability_total,
                "gear_score": r.gear_score,
            }
            for r in rows
        ]
    }
