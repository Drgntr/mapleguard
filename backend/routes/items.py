from fastapi import APIRouter, Query
from typing import Optional

from services.market_data import market_data_service
from services.rarity_engine import rarity_engine
from services.cache import cache_get, cache_set
from services.item_catalog import catalog_service
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/items", tags=["Items"])

# Category numbers for equipment slot types (from MSU marketplace)
SLOT_CATEGORIES: dict[str, list[int]] = {
    "weapon":    [1000101, 1000102],  # One-handed + Two-handed weapons
    "secondary": [1000103],           # Secondary weapons
    "hat":       [1000201001],
    "top":       [1000201002, 1000201003],  # Top + Outfit
    "bottom":    [1000201004],
    "shoes":     [1000201005],
    "gloves":    [1000201006],
    "cape":      [1000201007],
    "shoulder":  [1000201008],
    "face":      [1000202001],
    "eye":       [1000202002],
    "earring":   [1000202003],
    "ring":      [1000202004],
    "pendant":   [1000202005],
    "belt":      [1000202006],
    "pocket":    [1000202008],
    "badge":     [1000202009],
    "emblem":    [1000202010],
}


@router.get("/upgrades")
async def upgrade_suggestions(
    slot: str = Query(..., description="Equipment slot type (weapon, hat, etc.)"),
    current_sf: int = Query(0, ge=0, description="Current equipped item starforce"),
    current_grade: int = Query(0, ge=0, description="Current equipped item potential grade (0-4)"),
    limit: int = Query(20, ge=1, le=50),
):
    """Find marketplace items that could be upgrades for a given slot.
    Fetches items from marketplace, filters by slot category, and returns
    items with higher starforce or potential grade than currently equipped."""
    slot_key = slot.lower().replace(" ", "_")
    cats = SLOT_CATEGORIES.get(slot_key)
    if not cats:
        return {"items": [], "slot": slot, "error": f"Unknown slot: {slot}",
                "available_slots": list(SLOT_CATEGORIES.keys())}

    cache_key = f"upgrades:v2:{slot_key}:{current_sf}:{current_grade}:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Fetch marketplace items (API doesn't support category filter, so filter client-side)
    all_market = await market_data_service.fetch_all_items(max_pages=3)

    # Filter to matching categories
    cat_set = set(cats)
    slot_items = [
        item for item in all_market
        if item.category_no in cat_set
    ]

    upgrades = []
    for item in slot_items:
        sf_gain = item.starforce - current_sf
        grade_gain = item.potential_grade - current_grade
        bpot_gain = item.bonus_potential_grade
        if sf_gain > 0 or grade_gain > 0:
            score = sf_gain * 10 + grade_gain * 50 + bpot_gain * 20
            d = item.model_dump()
            d["sf_gain"] = sf_gain
            d["grade_gain"] = grade_gain
            d["upgrade_score"] = score
            upgrades.append(d)

    upgrades.sort(key=lambda x: x["upgrade_score"], reverse=True)
    result = {
        "items": upgrades[:limit],
        "slot": slot_key,
        "current_sf": current_sf,
        "current_grade": current_grade,
        "total_found": len(upgrades),
    }
    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_SECONDS)
    return result


@router.get("/catalog")
async def get_catalog(query: str = Query("")):
    """Get a list of common high-tier items for the calculator."""
    return {"items": catalog_service.get_catalog(query)}


@router.get("/")
async def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sorting: str = Query("ExploreSorting_RECENTLY_LISTED"),
    category_no: Optional[int] = None,
):
    """List marketplace items with filtering."""
    items, is_last = await market_data_service.fetch_items(
        page=page,
        page_size=page_size,
        sorting=sorting,
        category_no=category_no,
    )

    # Build fair values using floor prices from cache
    cache_key = "items:floor_prices_v3"
    cached = await cache_get(cache_key)
    floors = (cached or {}).get("floor_prices", {})

    def _get_fair(item):
        """Look up median from 4-level floor data."""
        name = item.name
        sf = f"SF{item.starforce}" if item.starforce > 0 else "NSF"
        pot = item.potential_grade
        bpot = item.bonus_potential_grade
        name_map = floors.get(name)
        if not name_map:
            return 0
        sf_map = name_map.get(sf)
        if not sf_map:
            # Try any SF bracket
            for v in name_map.values():
                if isinstance(v, dict):
                    sf_map = v
                    break
        if not sf_map:
            return 0
        pot_map = sf_map.get(str(pot))
        if not pot_map:
            # Try any potential
            for v in sf_map.values():
                if isinstance(v, dict):
                    pot_map = v
                    break
        if not pot_map:
            return 0
        bpot_info = pot_map.get(str(bpot))
        if bpot_info and isinstance(bpot_info, dict):
            return bpot_info.get("median", 0)
        # Fallback: any bpot
        for v in pot_map.values():
            if isinstance(v, dict) and v.get("median"):
                return v["median"]
        return 0

    result = []
    for i in items:
        d = i.model_dump()
        fair = _get_fair(i)
        d["fair_value_estimate"] = fair
        result.append(d)

    return {
        "items": result,
        "page": page,
        "page_size": page_size,
        "count": len(items),
        "is_last_page": is_last,
    }


@router.get("/recently-listed")
async def recently_listed(count: int = Query(30, ge=1, le=100)):
    """Get recently listed items and characters (normalized)."""
    data = await market_data_service.fetch_recently_listed(count)
    return {"listed": data, "count": len(data)}


@router.get("/consumables")
async def consumables():
    """Get consumable items with price and volume data."""
    data = await market_data_service.fetch_consumables()
    return {"items": [c.model_dump() for c in data], "count": len(data)}


@router.get("/underpriced")
async def underpriced_items(
    discount_threshold: float = Query(0.30, ge=0.05, le=0.95),
    limit: int = Query(50, ge=1, le=200),
):
    """Find items listed below their fair market value."""
    cache_key = f"underpriced:{discount_threshold}:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    items = await market_data_service.fetch_all_items(max_pages=3)

    rarity_engine.rebuild_index(items)
    underpriced = rarity_engine.find_underpriced(items, discount_threshold)

    result = {"items": underpriced[:limit], "count": min(len(underpriced), limit)}
    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_SECONDS)
    return result


@router.get("/lookup")
async def item_lookup(query: str = Query(..., description="Numeric marketplace ID, asset key (ITEM...), or item name")):
    """
    Flexible item lookup. Accepts:
    - Numeric NFT ID from marketplace URL (e.g. 8371514744002029434355400508674)
    - ITEM... asset key token ID
    - Item name (searches catalog + MSU marketplace)
    """
    q = query.strip()

    # 1. Numeric marketplace listing ID (big number) — get assetKey, then Open API
    if q.isdigit():
        cache_key = f"lookup_numeric_v3:{q}"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        try:
            # First get assetKey from marketplace, then fetch detail via Open API
            item = await market_data_service.fetch_item_detail(q)
            if item:
                result = item.model_dump()
                result["source"] = "openapi"
                await cache_set(cache_key, result, ttl=3600)
                return {"item": result}
            return {"error": f"Item not found for ID: {q}", "query": q}
        except Exception as e:
            return {"error": f"Lookup failed: {str(e)}", "query": q}

    # 2. Asset key (ITEM...)
    if q.upper().startswith("ITEM"):
        cache_key = f"lookup_asset_v2:{q}"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        
        item = await market_data_service.fetch_item_detail(q)
        if item:
            return {"item": {**item.model_dump(), "source": "asset_key"}}
        return {"error": "Asset key not found", "query": q}

    # 3. Name search — first check local catalog
    catalog_hits = catalog_service.get_catalog(q)
    if catalog_hits:
        # Return best match with base stats stub
        best = catalog_hits[0]
        result = {
            "item_id": best["item_id"],
            "name": best["name"],
            "required_level": best.get("level", 0),
            "starforce": 0,
            "potential_grade": 0,
            "bonus_potential_grade": 0,
            "image_url": f"https://api-static.msu.io/itemimages/icon/{best['item_id']}.png",
            "source": "catalog",
        }
        return {"item": result, "all_results": catalog_hits[:24]}

    # 4. Name search — fall back to MSU marketplace explore via POST
    try:
        # The explore endpoint only accepts POST; scan a page and match by name
        search_url = f"{settings.MSU_API_BASE}/marketplace/explore/items"
        body = {
            "filter": {"price": {"min": 0, "max": 10_000_000_000}},
            "sorting": "ExploreSorting_RECENTLY_LISTED",
            "paginationParam": {"pageNo": 1, "pageSize": 50},
        }
        raw = market_data_service._post(search_url, body, ITEM_HEADERS)
        raw_items = raw.get("items", raw.get("data", []))
        kw = q.lower()
        matches = []
        for it in raw_items:
            title = it.get("name", "").lower()
            if kw in title:
                data = it.get("data", {})
                sales = it.get("salesInfo", {})
                matches.append({
                    "item_id": data.get("itemId"),
                    "name": it.get("name", ""),
                    "token_id": str(it.get("tokenId", "")),
                    "starforce": data.get("starforce", 0),
                    "potential_grade": data.get("potentialGrade", 0),
                    "required_level": data.get("requiredLevel", 0),
                    "image_url": it.get("imageUrl", ""),
                    "price_wei": str(sales.get("priceWei", "0")),
                    "source": "marketplace_search",
                })
                if len(matches) >= 6:
                    break
        if matches:
            return {"item": matches[0], "all_results": matches}
    except Exception:
        pass

    return {"error": "Item not found", "query": q}


@router.get("/floor-prices")
async def item_floor_prices():
    """Compute floor prices by (item_name, starforce_bracket, potential_grade, bonus_potential_grade)."""
    cache_key = "items:floor_prices_v3"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    items = await market_data_service.fetch_all_items(max_pages=3)

    floors: dict[str, dict[str, dict[str, dict]]] = {}  # name -> sf_bracket -> pot_grade -> bpot_grade -> list[prices]

    for item in items:
        if item.price <= 0:
            continue
        name = item.name
        sf_bracket = f"SF{item.starforce}" if item.starforce > 0 else "NSF"
        pot_grade = item.potential_grade
        bpot_grade = item.bonus_potential_grade

        if name not in floors:
            floors[name] = {}
        if sf_bracket not in floors[name]:
            floors[name][sf_bracket] = {}
        if pot_grade not in floors[name][sf_bracket]:
            floors[name][sf_bracket][pot_grade] = {}
        if bpot_grade not in floors[name][sf_bracket][pot_grade]:
            floors[name][sf_bracket][pot_grade][bpot_grade] = []

        floors[name][sf_bracket][pot_grade][bpot_grade].append(item.price)

    result = {}
    for name, sf_map in floors.items():
        result[name] = {}
        for sf, grade_map in sf_map.items():
            result[name][sf] = {}
            for grade_str, bpot_map in grade_map.items():
                result[name][sf][grade_str] = {}
                for bpot_str, prices in bpot_map.items():
                    prices.sort()
                    median = prices[len(prices) // 2]
                    result[name][sf][grade_str][bpot_str] = {
                        "floor": prices[0],
                        "median": median,
                        "count": len(prices),
                    }

    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_LONG)
    return {"floor_prices": result, "sample_size": len(items)}


@router.get("/{token_id}/detail")
async def item_detail(token_id: str):
    """Get full item detail with stats, potentials, and scarcity score."""
    item = await market_data_service.fetch_item_detail(token_id)
    if not item:
        return {"error": "Item not found", "token_id": token_id}

    # Compute scarcity if engine is populated
    score = None
    if rarity_engine._total_items > 0:
        score = rarity_engine.compute_score(item).model_dump()

    return {"item": item.model_dump(), "scarcity": score}


@router.get("/{token_id}/scarcity")
async def item_scarcity(token_id: str):
    """Get scarcity score for a specific item."""
    cache_key = f"scarcity:{token_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Need index populated
    if rarity_engine._total_items == 0:
        items = await market_data_service.fetch_all_items(max_pages=3)
        rarity_engine.rebuild_index(items)

    # Find in existing index or fetch detail
    target = next((i for i in rarity_engine._items if i.token_id == token_id), None)
    if not target:
        target = await market_data_service.fetch_item_detail(token_id)

    if not target:
        return {"error": "Item not found", "token_id": token_id}

    score = rarity_engine.compute_score(target)
    result = score.model_dump()
    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_LONG)
    return result


@router.get("/trade-history/{item_id}")
async def trade_history(
    item_id: int,
    page_size: int = Query(50, ge=1, le=200),
):
    """Get trade history for an item type."""
    trades = await market_data_service.fetch_trade_history(item_id, page_size)
    return {
        "item_id": item_id,
        "trades": [t.model_dump() for t in trades],
        "count": len(trades),
    }


@router.get("/ohlc/{item_id}")
async def item_ohlc(
    item_id: int,
    interval: int = Query(60, description="Interval in minutes"),
):
    """Get OHLC candlestick data from trade history."""
    cache_key = f"ohlc:{item_id}:{interval}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    trades = await market_data_service.fetch_trade_history(item_id, page_size=200)
    bars = market_data_service.compute_ohlc(trades, interval)

    result = {
        "item_id": item_id,
        "interval_minutes": interval,
        "bars": [b.model_dump() for b in bars],
        "trade_count": len(trades),
    }
    await cache_set(cache_key, result, ttl=settings.CACHE_TTL_SECONDS)
    return result
