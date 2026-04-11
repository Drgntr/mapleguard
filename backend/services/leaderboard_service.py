"""
Leaderboard Service — Character CP and marketplace leaderboard.

Groups characters by class/subclass with CP data computed from
cached character details and cross-references whale tracker data.
"""
import asyncio
from collections import defaultdict
from typing import Dict, List

from services.market_data import market_data_service
from services.cache import cache_get, cache_set

try:
    from services.combat_power_engine import combat_power_engine
except ImportError:
    combat_power_engine = None


try:
    from services.whale_tracker import whale_tracker
except ImportError:
    whale_tracker = None


try:
    from config import get_settings
    settings = get_settings()
except ImportError:
    class _FakeSettings:
        CACHE_TTL_LONG = 300
    settings = _FakeSettings()


class LeaderboardService:
    def __init__(self):
        self._cache: dict = {}

    async def _get_char_cp(self, char) -> int:
        """Compute CP for a character listing.

        Priority:
        1. Use cached combat_power from Open API detail (fast)
        2. Fallback: estimate from price * level multiplier
        """
        price = getattr(char, "price", 0) or 0
        level = getattr(char, "level", 0) or 0

        # Check cache for detail with combat_power
        cache_key = f"char_detail_v12:{char.token_id}"
        cached_detail = await cache_get(cache_key)

        if cached_detail and cached_detail.get("ap_stats"):
            ap_data = cached_detail["ap_stats"]
            if isinstance(ap_data, dict):
                cp_block = ap_data.get("combat_power", {})
                if isinstance(cp_block, dict):
                    cp = int(cp_block.get("total", 0) or 0)
                    if cp > 0:
                        return cp

        # Fallback: estimate from price and level
        level_mult = 1.0 + (level / 300.0)
        return max(int(price * 2 * level_mult), 0)

    async def compute_by_class(self, class_name: str = None, limit: int = 50) -> dict:
        """Compute leaderboard for a specific class, or all classes if None."""
        cache_key = f"leaderboard:v2:{class_name or 'all'}:{limit}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        all_chars = await market_data_service.fetch_all_characters(max_pages=6)

        # Deduplicate by token_id
        seen: set = set()
        unique_chars = []
        for char in all_chars:
            tid = getattr(char, "token_id", "")
            if tid and tid not in seen:
                seen.add(tid)
                unique_chars.append(char)

        groups: dict = defaultdict(list)
        for char in unique_chars:
            cls = getattr(char, "class_name", "") or "Unknown"
            groups[cls].append(char)

        result: dict[str, list] = {}
        target_classes = [class_name] if class_name else sorted(groups.keys())

        for cls in target_classes:
            chars = groups.get(cls, [])
            if not chars:
                continue

            char_entries = []
            max_computes = 20
            chars_sorted = sorted(chars, key=lambda c: getattr(c, "price", 0) or 0, reverse=True)

            for char in chars_sorted[:max_computes]:
                cp = await self._get_char_cp(char)
                char_entries.append({
                    "token_id": char.token_id,
                    "name": getattr(char, "name", "") or "",
                    "class_name": cls,
                    "level": getattr(char, "level", 0) or 0,
                    "price": getattr(char, "price", 0) or 0,
                    "cp": cp,
                    "image_url": getattr(char, "image_url", ""),
                })

            char_entries.sort(key=lambda x: x["cp"], reverse=True)
            result[cls] = char_entries[:limit]

        output = {
            "classes": result,
            "total_classes": len(result),
            "total_characters": sum(len(v) for v in result.values()),
        }

        await cache_set(cache_key, output, ttl=settings.CACHE_TTL_LONG)
        return output

    async def compute_combined(self, limit: int = 100) -> dict:
        """Combined leaderboard: top CP characters across all classes."""
        cache_key = f"leaderboard:combined:{limit}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        all_chars = await market_data_service.fetch_all_characters(max_pages=6)

        # Deduplicate by token_id
        seen: set = set()
        unique_chars = []
        for char in all_chars:
            tid = getattr(char, "token_id", "")
            if tid and tid not in seen:
                seen.add(tid)
                unique_chars.append(char)

        candidates = sorted(
            unique_chars,
            key=lambda c: (getattr(c, "level", 0) or 0) * 0.6 + (getattr(c, "price", 0) or 0) * 0.4,
            reverse=True,
        )[:min(len(unique_chars), 100)]

        entries = []
        compute_count = 0
        max_computes = 50

        for char in candidates:
            if compute_count >= max_computes:
                cp = int(getattr(char, "price", 0) or 0) * 2
            else:
                try:
                    cp = await self._get_char_cp(char)
                except Exception:
                    cp = int(getattr(char, "price", 0) or 0) * 2

            entries.append({
                "token_id": char.token_id,
                "name": getattr(char, "name", "") or "",
                "class_name": getattr(char, "class_name", "") or "Unknown",
                "level": getattr(char, "level", 0) or 0,
                "price": getattr(char, "price", 0) or 0,
                "cp": cp,
                "image_url": getattr(char, "image_url", ""),
            })
            compute_count += 1

        entries.sort(key=lambda x: x["cp"], reverse=True)

        output = {
            "top_characters": entries[:limit],
            "total_scored": len(entries),
        }

        await cache_set(cache_key, output, ttl=settings.CACHE_TTL_LONG)
        return output


leaderboard_service = LeaderboardService()
