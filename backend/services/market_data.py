"""
Market Data Service - fetches, parses, and caches marketplace data from:
  1. MSU Open API (official, API-key authenticated) for character/item details
  2. MSU Marketplace API (curl_cffi TLS impersonation) for explore/listing data
  3. MSU Navigator API (legacy) for trade history (no Open API equivalent yet)

API architecture (April 2026):
- Open API (openapi.msu.io/v1rc1): Character & Item detail, Enhancement pricing, GameMeta
- Marketplace (msu.io/marketplace/api): Explore listings, recently-listed, consumables
- Navigator (msu.io/navigator/api/navigator): Trade history
"""

import asyncio
import os
import httpx
from curl_cffi import requests as cffi_requests
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from config import get_settings
from models.item import ItemListing, ConsumableListing, TradeRecord, OHLCBar
from models.character import CharacterListing
from services.cache import cache_get, cache_set

settings = get_settings()

# ─── Headers ──────────────────────────────────────────────────────────

# Marketplace API (requires browser-like TLS fingerprint)
CHAR_HEADERS = {
    "accept": "*/*",
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/json",
    "origin": "https://msu.io",
    "referer": "https://msu.io/",
}

ITEM_HEADERS = {
    "accept": "*/*",
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/json",
    "origin": "https://msu.io",
    "referer": "https://msu.io/marketplace/nft",
}

XANGLE_HEADERS = {
    "accept": "application/json",
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/json",
    "origin": "https://msu-explorer.xangle.io",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "x-chain": "NEXON",
    "x-secret-key": os.environ.get("XANGLE_SECRET_KEY", "PLACEHOLDER_KEY_REMOVED"),
}


class MarketDataService:
    """Fetches and transforms marketplace data from MSU APIs."""

    def __init__(self):
        self._httpx_client: Optional[httpx.Client] = None

    @property
    def _openapi_client(self) -> httpx.Client:
        """Lazy-init httpx client for MSU Open API (clean HTTP, no TLS impersonation)."""
        if self._httpx_client is None or self._httpx_client.is_closed:
            self._httpx_client = httpx.Client(
                base_url=settings.MSU_OPENAPI_BASE,
                headers={
                    "accept": "application/json",
                    "x-nxopen-api-key": settings.MSU_OPENAPI_KEY,
                },
                timeout=20.0,
            )
        return self._httpx_client

    # ─── HTTP helpers ─────────────────────────────────────────────────

    def _get(self, url: str, headers: dict = None, params: dict = None) -> dict:
        """GET via curl_cffi (marketplace/navigator — needs TLS impersonation)."""
        r = cffi_requests.get(
            url,
            headers=headers or ITEM_HEADERS,
            params=params,
            impersonate="chrome",
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def _post(self, url: str, body: dict, headers: dict = None) -> dict:
        """POST via curl_cffi (marketplace — needs TLS impersonation)."""
        r = cffi_requests.post(
            url,
            headers=headers or ITEM_HEADERS,
            json=body,
            impersonate="chrome",
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def _get_openapi(self, path: str, params: dict = None) -> Optional[dict]:
        """GET from MSU Open API. Returns data payload or None on error.
        Path should be relative, e.g. '/characters/by-token-id/123'."""
        try:
            r = self._openapi_client.get(path, params=params)
            r.raise_for_status()
            body = r.json()
            if body.get("success"):
                return body.get("data")
            print(f"[OpenAPI] Error in {path}: {body.get('error', {}).get('message', 'unknown')}")
            return None
        except Exception as e:
            print(f"[OpenAPI] Request failed for {path}: {e}")
            return None

    def _get_openapi_sync(self, path: str) -> Optional[dict]:
        """Synchronous Open API call (for use in non-async contexts like calculator)."""
        return self._get_openapi(path)

    # ─── Recently Listed ──────────────────────────────────────────────

    async def fetch_recently_listed(self, count: int = 30) -> list[dict]:
        """Fetch recently listed items/characters (no count param - API rejects it)."""
        cache_key = "recent"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        url = f"{settings.MSU_API_BASE}/marketplace/dashboard/recently-listed"
        # API now rejects 'count' parameter — call without params
        raw = self._get(url, ITEM_HEADERS)
        listed = raw.get("listed", [])

        normalized = []
        for entry in listed[:count]:
            token_type = entry.get("tokenInfo", {}).get("tokenType", "items")
            sales = entry.get("salesInfo", {})
            price_wei = sales.get("priceWei", "0")

            try:
                price = int(price_wei) / 1e18
            except (ValueError, TypeError):
                price = 0.0

            item = {
                "token_id": str(entry.get("tokenId", "")),
                "name": entry.get("name", ""),
                "token_type": token_type,
                "price_wei": str(price_wei),
                "price": price,
                "created_at": sales.get("createdAt"),
                "image_url": entry.get("imageUrl"),
            }

            if token_type == "characters":
                char = entry.get("character", entry.get("data", {}))
                job = char.get("job", {})
                item["class_name"] = job.get("className", "")
                item["job_name"] = job.get("jobName", "")
                item["level"] = char.get("level", 0)
            else:
                it = entry.get("item", entry.get("data", {}))
                item["starforce"] = it.get("starforce", 0)
                item["potential_grade"] = it.get("potentialGrade", 0)
                item["item_name"] = it.get("name", entry.get("name", ""))

            normalized.append(item)

        await cache_set(cache_key, normalized, ttl=settings.CACHE_TTL_SECONDS)
        return normalized

    # ─── Items ────────────────────────────────────────────────────────

    async def fetch_items(
        self,
        page: int = 1,
        page_size: int = 135,
        sorting: str = "ExploreSorting_RECENTLY_LISTED",
        price_min: int = 0,
        price_max: int = 10_000_000_000,
        category_no: Optional[int] = None,
    ) -> tuple[list[ItemListing], bool]:
        """Fetch items from explore endpoint."""
        cache_key = f"items:{page}:{page_size}:{sorting}:{category_no}"
        cached = await cache_get(cache_key)
        if cached:
            return [ItemListing(**i) for i in cached["items"]], cached["is_last"]

        url = f"{settings.MSU_API_BASE}/marketplace/explore/items"
        body: dict = {
            "filter": {
                "price": {"min": price_min, "max": price_max},
            },
            "sorting": sorting,
            "paginationParam": {
                "pageNo": page,
                "pageSize": page_size,
            },
        }
        if category_no is not None:
            body["filter"]["categoryNo"] = category_no

        # If MSU API rejects non-RECENTLY_LISTED sorting, fall back to
        # fetching RECENTLY_LISTED and sorting client-side
        try:
            data = self._post(url, body, ITEM_HEADERS)
        except Exception:
            body["sorting"] = "ExploreSorting_RECENTLY_LISTED"
            data = self._post(url, body, ITEM_HEADERS)
            raw_items = data.get("items", [])
            is_last = data.get("paginationResult", {}).get("isLastPage", True)
            items = [ItemListing.from_explore_api(r) for r in raw_items]
            if sorting == "ExploreSorting_PRICE_LOW_TO_HIGH":
                items.sort(key=lambda x: x.price)
            elif sorting == "ExploreSorting_PRICE_HIGH_TO_LOW":
                items.sort(key=lambda x: x.price, reverse=True)
            await cache_set(
                cache_key,
                {"items": [i.model_dump() for i in items], "is_last": is_last},
                ttl=settings.CACHE_TTL_SECONDS,
            )
            return items, is_last

        raw_items = data.get("items", [])
        is_last = data.get("paginationResult", {}).get("isLastPage", True)

        items = [ItemListing.from_explore_api(r) for r in raw_items]

        await cache_set(
            cache_key,
            {"items": [i.model_dump() for i in items], "is_last": is_last},
            ttl=settings.CACHE_TTL_SECONDS,
        )
        return items, is_last

    async def fetch_all_items(self, max_pages: int = 5, **kwargs) -> list[ItemListing]:
        """Fetch multiple pages of items."""
        all_items = []
        for page in range(1, max_pages + 1):
            items, is_last = await self.fetch_items(page=page, **kwargs)
            all_items.extend(items)
            if is_last:
                break
        return all_items

    async def fetch_item_detail(self, token_id: str) -> Optional[ItemListing]:
        """Fetch full item detail with stats and potentials.
        Uses MSU Open API (primary) with marketplace fallback."""
        cache_key = f"item_detail_v2:{token_id}"
        cached = await cache_get(cache_key)
        if cached:
            return ItemListing(**cached)

        # 1. Open API — by asset key (ITEM...) or via marketplace lookup for numeric IDs
        if token_id.upper().startswith("ITEM"):
            data = self._get_openapi(f"/items/{token_id}")
            if data and data.get("item"):
                try:
                    item = ItemListing.from_openapi(data["item"])
                    await cache_set(cache_key, item.model_dump(), ttl=settings.CACHE_TTL_LONG)
                    return item
                except Exception as e:
                    print(f"[OpenAPI] Item parse error for {token_id}: {e}")

        # 2. For numeric token IDs — get assetKey from marketplace, then use Open API
        if token_id.isdigit() or (not token_id.upper().startswith("ITEM")):
            try:
                url = f"{settings.MSU_API_BASE}/marketplace/items/{token_id}"
                mkt_data = self._get(url, ITEM_HEADERS)
                asset_key = mkt_data.get("assetKey", "")

                # Try Open API with the discovered assetKey
                if asset_key and asset_key.upper().startswith("ITEM"):
                    oapi_data = self._get_openapi(f"/items/{asset_key}")
                    if oapi_data and oapi_data.get("item"):
                        try:
                            item = ItemListing.from_openapi(oapi_data["item"])
                            # Preserve marketplace sales info
                            sales = mkt_data.get("salesInfo", {})
                            if sales.get("priceWei"):
                                item.price_wei = str(sales["priceWei"])
                            if sales.get("createdAt"):
                                item.created_at = sales["createdAt"]
                            await cache_set(cache_key, item.model_dump(), ttl=settings.CACHE_TTL_LONG)
                            return item
                        except Exception as e:
                            print(f"[OpenAPI] Item parse error for {asset_key}: {e}")

                # Fallback: parse marketplace data directly
                item = ItemListing.from_detail_api(mkt_data)
                await cache_set(cache_key, item.model_dump(), ttl=settings.CACHE_TTL_LONG)
                return item
            except Exception:
                pass

        return None

    # ─── Characters ───────────────────────────────────────────────────

    async def fetch_characters(
        self,
        page: int = 1,
        page_size: int = 135,
        class_filter: str = "all_classes",
        level_min: int = 0,
        level_max: int = 300,
        price_min: int = 0,
        price_max: int = 10_000_000_000,
    ) -> tuple[list[CharacterListing], bool, int]:
        """
        Fetch characters. NOTE: 'sorting' field causes 400 on the
        characters endpoint — we omit it entirely.
        """
        cache_key = f"chars_v2:{page}:{page_size}:{class_filter}:{level_min}:{level_max}"
        cached = await cache_get(cache_key)
        if cached:
            return [CharacterListing(**c) for c in cached["chars"]], cached["is_last"], cached.get("total", 0)

        url = f"{settings.MSU_API_BASE}/marketplace/explore/characters"
        body = {
            "filter": {
                "price": {"min": price_min, "max": price_max},
                "level": {"min": level_min, "max": level_max},
            },
            "paginationParam": {
                "pageNo": page,
                "pageSize": page_size,
            },
        }
        
        # Only add class filter IF it is not 'all'
        if class_filter and class_filter != "all_classes":
            body["filter"]["className"] = class_filter
        # job filter is not supported by the API

        data = self._post(url, body, CHAR_HEADERS)
        raw_chars = data.get("characters", [])
        pag = data.get("paginationResult", {})
        is_last = pag.get("isLastPage", True)
        total_count = pag.get("totalCount", 0)

        chars = [CharacterListing.from_explore_api(r) for r in raw_chars]

        await cache_set(
            cache_key,
            {"chars": [c.model_dump() for c in chars], "is_last": is_last, "total": total_count},
            ttl=settings.CACHE_TTL_SECONDS,
        )
        return chars, is_last, total_count

    async def fetch_all_characters(self, max_pages: int = 5, **kwargs) -> list[CharacterListing]:
        all_chars = []
        for page in range(1, max_pages + 1):
            chars, is_last, _ = await self.fetch_characters(page=page, **kwargs)
            all_chars.extend(chars)
            if is_last:
                break
        return all_chars

    async def fetch_character_detail(self, token_id: str) -> Optional[CharacterListing]:
        """Fetch full character detail with AP stats and equipment.
        Uses MSU Open API (primary) with marketplace fallback."""
        cache_key = f"char_detail_v12:{token_id}"
        cached = await cache_get(cache_key)
        if cached:
            return CharacterListing(**cached)

        # 1. Navigator + Open API item enrichment — for CHAR asset keys
        if token_id.upper().startswith("CHAR"):
            try:
                nav_url = f"https://msu.io/navigator/api/navigator/characters/{token_id}/info"
                nav_data = self._get(nav_url, CHAR_HEADERS)
                char_node = nav_data.get("character") if nav_data else None
                if char_node:
                    wearing = char_node.get("wearing", {})

                    # Collect all ITEM asset keys for enrichment
                    item_asset_keys: list[str] = []
                    def _walk_nav(d):
                        if not isinstance(d, dict):
                            return
                        ak = d.get("assetKey")
                        if ak and isinstance(ak, str) and ak.upper().startswith("ITEM"):
                            item_asset_keys.append(ak)
                            return
                        for v in d.values():
                            if isinstance(v, dict):
                                _walk_nav(v)
                            elif isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict):
                                        _walk_nav(item)
                    _walk_nav(wearing)
                    item_asset_keys = list(set(item_asset_keys))

                    # Enrich items via Open API /items/{assetKey}
                    rich_items: dict[str, dict] = {}
                    if item_asset_keys:
                        print(f"[Navigator+OpenAPI] Enriching {len(item_asset_keys)} items for {token_id}...")
                        for ak in item_asset_keys:
                            try:
                                item_data = self._get_openapi(f"/items/{ak}")
                                if item_data:
                                    rich_items[ak] = item_data
                            except Exception:
                                pass

                    # Merge enriched data into wearing slots
                    for equip_type in ("equip", "cashEquip", "pet"):
                        slots = wearing.get(equip_type, {})
                        if not isinstance(slots, dict):
                            continue
                        for slot_name, slot_data in slots.items():
                            if not isinstance(slot_data, dict) or not slot_data:
                                continue
                            ak = slot_data.get("assetKey", "")
                            if ak and ak in rich_items:
                                rich = rich_items[ak].get("item", {})
                                slot_data["enhance"] = rich.get("enhance", {})
                                slot_data["stats"] = rich.get("stats", {})
                                slot_data["common"] = rich.get("common", {})
                                name = rich.get("common", {}).get("itemName", "")
                                if name:
                                    slot_data["name"] = name
                                    slot_data["itemName"] = name
                                slot_data["imageUrl"] = slot_data.get("imageUrl") or rich.get("image", {}).get("imageUrl", "")

                    reshaped = {
                        "tokenId": char_node.get("tokenInfo", {}).get("tokenId", ""),
                        "assetKey": char_node.get("assetKey", token_id),
                        "name": char_node.get("name", ""),
                        "imageUrl": char_node.get("imageUrl", ""),
                        "character": {
                            "common": char_node.get("common", {}),
                            "apStat": char_node.get("apStat", {}),
                            "wearing": wearing,
                            "hyperStat": char_node.get("hyperStat", {}),
                            "ability": char_node.get("ability", {}),
                        },
                    }
                    char = CharacterListing.from_detail_api(reshaped)
                    if char:
                        char.asset_key = token_id
                        if not char.token_id or char.token_id in ("", "None"):
                            char.token_id = token_id
                        await cache_set(cache_key, char.model_dump(), ttl=settings.CACHE_TTL_LONG)
                        return char
            except Exception as e:
                print(f"[Navigator] Info error for {token_id}: {e}")

            # 1b. Full fallback: Open API character + item enrichment
            char = await self._fetch_openapi_character_detail(token_id, by_asset_key=True)
            if char:
                await cache_set(cache_key, char.model_dump(), ttl=settings.CACHE_TTL_LONG)
                return char

        # 2. Open API — by numeric token ID
        if not token_id.upper().startswith("CHAR"):
            char = await self._fetch_openapi_character_detail(token_id, by_asset_key=False)
            if char:
                # Try to get marketplace sales info to preserve price
                try:
                    url = f"{settings.MSU_API_BASE}/marketplace/characters/{token_id}"
                    mkt_data = self._get(url, CHAR_HEADERS)
                    sales = mkt_data.get("salesInfo", {})
                    if sales.get("priceWei"):
                        char.price_wei = str(sales["priceWei"])
                    if sales.get("createdAt"):
                        char.created_at = sales["createdAt"]
                except Exception:
                    pass  # Sales info is optional
                await cache_set(cache_key, char.model_dump(), ttl=settings.CACHE_TTL_LONG)
                return char

        # 3. Fallback: marketplace API directly
        try:
            url = f"{settings.MSU_API_BASE}/marketplace/characters/{token_id}"
            data = self._get(url, CHAR_HEADERS)
            char = CharacterListing.from_detail_api(data)
            await cache_set(cache_key, char.model_dump(), ttl=settings.CACHE_TTL_LONG)
            return char
        except Exception as e:
            print(f"Character detail error for {token_id}: {e}")
            return None

    # ─── Character Search (Marketplace scan) ────────────────────────────

    async def search_navigator_characters(self, keyword: str) -> list[dict]:
        """Search characters globally via Navigator search API."""
        results = []
        seen: set[str] = set()

        # 1. Navigator search API — finds ALL characters (not just marketplace)
        try:
            nav_url = f"https://msu.io/navigator/api/navigator/search?keyword={keyword}&limit=20"
            data = self._get(nav_url, CHAR_HEADERS)
            for record in data.get("records", []):
                if record.get("type") != "character":
                    continue
                char_info = record.get("character", {})
                asset_key = char_info.get("assetKey", "")
                name = char_info.get("characterName", "")
                job = char_info.get("job", {})
                if asset_key and asset_key not in seen:
                    seen.add(asset_key)
                    results.append({
                        "token_id": asset_key,
                        "name": name,
                        "level": char_info.get("level", 0),
                        "class_name": job.get("className", ""),
                        "job_name": job.get("jobName", ""),
                        "image_url": record.get("imageUrl"),
                    })
        except Exception as e:
            print(f"[search] Navigator search error: {e}")

        # 2. Fallback: scan marketplace explore listings
        if not results:
            kw_lower = keyword.lower()
            try:
                body = {
                    "filter": {"class": "all_classes", "price": {"min": 0, "max": 10_000_000_000}, "level": {"min": 0, "max": 300}},
                    "paginationParam": {"pageNo": 1, "pageSize": 135},
                }
                data = self._post(f"{settings.MSU_API_BASE}/marketplace/explore/characters", body, CHAR_HEADERS)
                for r in data.get("characters", []):
                    name = r.get("name", "")
                    if kw_lower in name.lower():
                        tid = str(r.get("tokenId", ""))
                        if tid and tid not in seen:
                            seen.add(tid)
                            char_block = r.get("character", {})
                            common = char_block.get("common", {})
                            job = common.get("job", {})
                            results.append({
                                "token_id": tid,
                                "name": name,
                                "level": common.get("level", 0),
                                "class_name": job.get("className", ""),
                                "job_name": job.get("jobName", ""),
                                "image_url": r.get("imageUrl"),
                            })
            except Exception as e:
                print(f"[search] Marketplace fallback error: {e}")

        return results

    # ─── Open API Character Detail (with item enrichment) ─────────────

    async def _fetch_openapi_character_detail(
        self, identifier: str, by_asset_key: bool = True
    ) -> Optional[CharacterListing]:
        """Fetch character details from MSU Open API with enriched equipped item stats.
        Uses all-in-one endpoint, then enriches minted items via /items/{assetKey}."""
        # 1. Get character data from Open API
        if by_asset_key:
            path = f"/characters/{identifier}"
        else:
            path = f"/characters/by-token-id/{identifier}"

        data = self._get_openapi(path)
        if not data or not data.get("character"):
            return None

        raw_char = data["character"]

        # 2. Extract asset keys for equipped items that need enrichment
        wearing = raw_char.get("wearing", {})
        asset_keys: list[str] = []

        def _walk(d):
            if not isinstance(d, dict):
                return
            ak = d.get("assetKey")
            if ak and isinstance(ak, str) and ak.upper().startswith("ITEM"):
                asset_keys.append(ak)
                return
            for v in d.values():
                if isinstance(v, dict):
                    _walk(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            _walk(item)
        _walk(wearing)
        asset_keys = list(set(asset_keys))

        # 3. Enrich minted items via Open API /items/{assetKey}
        rich_items: dict[str, dict] = {}
        if asset_keys:
            print(f"[OpenAPI] Enriching {len(asset_keys)} items for {identifier}...")
            for i, ak in enumerate(asset_keys):
                item_data = self._get_openapi(f"/items/{ak}")
                if item_data:
                    rich_items[ak] = item_data  # {"item": {...}} — matches expected format
                    if i < 2:
                        print(f"  [Enrich] OK: {ak[:20]}")

        # 4. Parse using from_openapi + enrich with item data
        from models.character import CharacterListing

        # Build enriched wearing: merge rich_items data into the wearing slots
        for equip_type in ("equip", "cashEquip", "pet"):
            slots = wearing.get(equip_type if equip_type != "cashEquip" else "decoEquip", {})
            if equip_type == "equip":
                slots = wearing.get("equip", {})
            elif equip_type == "cashEquip":
                slots = wearing.get("decoEquip", {})
            elif equip_type == "pet":
                slots = wearing.get("pet", {})

            if not isinstance(slots, dict):
                continue
            for slot_name, slot_data in slots.items():
                if not isinstance(slot_data, dict) or not slot_data:
                    continue
                ak = slot_data.get("assetKey", "")
                if ak and ak in rich_items:
                    rich = rich_items[ak].get("item", {})
                    # Merge rich item data into the wearing slot
                    slot_data["enhance"] = rich.get("enhance", {})
                    slot_data["stats"] = rich.get("stats", {})
                    slot_data["common"] = rich.get("common", {})
                    name = rich.get("common", {}).get("itemName", "")
                    if name:
                        slot_data["name"] = name
                        slot_data["itemName"] = name

        char = CharacterListing.from_openapi(raw_char)
        return char

    # ─── Trade History (Navigator — no Open API equivalent yet) ────────

    async def fetch_trade_history(
        self, item_id: int, page_size: int = 50
    ) -> list[TradeRecord]:
        """Fetch trade history for an item type from the Navigator API.
        NOTE: No Open API equivalent exists yet, keeping Navigator endpoint."""
        cache_key = f"trades:{item_id}:{page_size}"
        cached = await cache_get(cache_key)
        if cached:
            return [TradeRecord(**t) for t in cached]

        url = f"{settings.MSU_NAVIGATOR_BASE}/msu-stats/trade-history/items/{item_id}"
        try:
            data = self._get(url, ITEM_HEADERS, {"scrollParam.pageSize": page_size})
            histories = data.get("tradeHistories", [])
            trades = [
                TradeRecord(
                    price_wei=str(h.get("priceWei", "0")),
                    created_at=h.get("createdAt"),
                )
                for h in histories
            ]
            await cache_set(
                cache_key, [t.model_dump() for t in trades], ttl=settings.CACHE_TTL_LONG
            )
            return trades
        except Exception:
            return []

    # ─── Consumables ──────────────────────────────────────────────────

    async def fetch_consumables(self) -> list[ConsumableListing]:
        """Fetch consumable items."""
        cache_key = "consumables"
        cached = await cache_get(cache_key)
        if cached:
            return [ConsumableListing(**c) for c in cached]

        url = f"{settings.MSU_API_BASE}/marketplace/explore/consumables"
        data = self._get(url, ITEM_HEADERS)
        raw = data.get("items", [])
        consumables = [ConsumableListing.from_api(r) for r in raw]
        await cache_set(
            cache_key,
            [c.model_dump() for c in consumables],
            ttl=settings.CACHE_TTL_SECONDS,
        )
        return consumables

    # ─── Explorer (Xangle) ────────────────────────────────────────────

    async def fetch_xangle_transfers(self, size: int = 50) -> list[dict]:
        """Fetch rich NFT transfers directly from the Xangle explorer."""
        url = "https://api-gateway.xangle.io/api/nft/transfer/list"
        body = {"page": 1, "size": size}
        try:
            data = self._post(url, body, XANGLE_HEADERS)
            return data.get("NFTLIST", [])
        except Exception as e:
            print(f"Xangle fetch error: {e}")
            return []

    # ─── OHLC ─────────────────────────────────────────────────────────

    def compute_ohlc(
        self,
        trades: list[TradeRecord],
        interval_minutes: int = 60,
        item_name: str = "",
    ) -> list[OHLCBar]:
        if not trades:
            return []

        buckets: dict[datetime, list[float]] = defaultdict(list)
        for trade in trades:
            if not trade.created_at or trade.price <= 0:
                continue
            ts = trade.created_at
            if isinstance(ts, str):
                ts = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            bucket_ts = ts.replace(
                minute=(ts.minute // interval_minutes) * interval_minutes
                if interval_minutes < 60
                else 0,
                second=0,
                microsecond=0,
            )
            buckets[bucket_ts].append(trade.price)

        bars = []
        for ts in sorted(buckets.keys()):
            prices = buckets[ts]
            bars.append(
                OHLCBar(
                    timestamp=ts,
                    open=prices[0],
                    high=max(prices),
                    low=min(prices),
                    close=prices[-1],
                    volume=len(prices),
                    item_name=item_name,
                )
            )
        return bars

    async def close(self):
        """Cleanup HTTP clients."""
        if self._httpx_client and not self._httpx_client.is_closed:
            self._httpx_client.close()


# Singleton
market_data_service = MarketDataService()
