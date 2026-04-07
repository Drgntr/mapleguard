"""
Character Price Predictor — computes fair value estimates for characters.

Similar approach to rarity_engine for items:
- Index all indexed characters
- Group by (class_name, level_bracket, cp_bracket)
- Also considers equipment quality from explore API data
- Computes median and IQR-filtered median as fair value
"""

from collections import defaultdict
from typing import Optional

from models.character import CharacterListing
from services.combat_power_engine import combat_power_engine


class CharacterPricePredictor:
    """Predicts fair character prices based on marketplace distribution."""

    def __init__(self):
        self._chars: list[CharacterListing] = []
        self._total: int = 0
        # group_key -> [prices]
        self._price_by_group: dict[str, list[float]] = defaultdict(list)
        # group_key -> stats
        self._group_stats: dict[str, dict] = {}
        # character token_id -> fair value
        self._fair_cache: dict[str, float] = {}

    # ── Grouping keys ────────────────────────────────────────────────

    @staticmethod
    def _level_bracket(level: int) -> str:
        thresholds = [65, 120, 140, 160, 200, 220, 230, 240]
        current = "0"
        for t in thresholds:
            if level >= t:
                current = str(t)
            else:
                break
        return current

    @staticmethod
    def _cp_bracket(cp: float) -> str:
        """Bucket by combat power magnitude."""
        if cp <= 0:
            return "N"
        if cp < 100_000:
            return "A"
        if cp < 500_000:
            return "B"
        if cp < 1_000_000:
            return "C"
        if cp < 5_000_000:
            return "D"
        return "E"

    @staticmethod
    def _equip_quality(char: CharacterListing) -> str:
        """Rough equipment quality tier from available explore data."""
        # From explore API we don't have full equipment list.
        # Use level as a proxy + any available CP from char_cp
        cp = char.char_cp or 0
        if cp > 2_000_000:
            return "Q4"
        if cp > 200_000:
            return "Q3"
        if cp > 50_000:
            return "Q2"
        if cp > 0:
            return "Q1"
        return "Q0"

    def _group_key(self, char: CharacterListing) -> str:
        cls = char.class_name or "Unknown"
        lvl = self._level_bracket(char.level)
        cpb = self._cp_bracket(char.char_cp or 0)
        return f"{cls}|{lvl}|{cpb}"

    # ── Index management ─────────────────────────────────────────────

    def rebuild_index(self, chars: list[CharacterListing]):
        """Build price distribution index from marketplace data."""
        self._chars = chars
        self._total = len(chars)
        self._price_by_group.clear()
        self._fair_cache.clear()

        for char in chars:
            if char.price > 0:
                key = self._group_key(char)
                self._price_by_group[key].append(char.price)

        # Compute group stats
        self._group_stats.clear()
        for key, prices in self._price_by_group.items():
            self._group_stats[key] = self._compute_stats(prices)

    # ── Statistics ───────────────────────────────────────────────────

    @staticmethod
    def _compute_stats(prices: list[float]) -> dict:
        if not prices:
            return {"floor": 0, "median": 0, "mean": 0, "count": 0}

        sorted_p = sorted(prices)
        n = len(sorted_p)
        median = sorted_p[n // 2]

        # IQR filtering
        if n >= 4:
            q1 = sorted_p[n // 4]
            q3 = sorted_p[(3 * n) // 4]
            iqr = q3 - q1
            filtered = [p for p in sorted_p if q1 - 1.5 * iqr <= p <= q3 + 1.5 * iqr]
            if filtered:
                sorted_p = filtered
                n = len(sorted_p)
                median = sorted_p[n // 2]

        return {
            "floor": sorted(prices)[0],
            "median": round(median, 2),
            "mean": round(sum(prices) / len(prices), 2),
            "count": len(prices),
        }

    # ── Fair value ───────────────────────────────────────────────────

    def estimate_fair_value(self, char: CharacterListing) -> float:
        """
        Estimate fair value for a character.

        Strategy:
        1. Exact group match (class + level_bracket + cp_bracket) — best
        2. Fallback to class + level_bracket only
        3. Fallback to class-wide median
        """
        key = self._group_key(char)
        stats = self._group_stats.get(key)

        if stats and stats["count"] >= 2:
            return stats["median"]

        # Fallback: drop CP bracket, use class+level
        cls = char.class_name or "Unknown"
        lvl = self._level_bracket(char.level)
        class_level_key = f"{cls}|{lvl}|ANY"
        # Aggregate all CP tiers for this class+level
        total_prices = []
        for gkey, prices in self._price_by_group.items():
            if gkey.startswith(f"{cls}|{lvl}|"):
                total_prices.extend(prices)
        if len(total_prices) >= 2:
            s = self._compute_stats(total_prices)
            return s["median"]

        # Class-wide fallback
        class_prices = []
        for gkey, prices in self._price_by_group.items():
            if gkey.startswith(f"{cls}|"):
                class_prices.extend(prices)
        if class_prices:
            s = self._compute_stats(class_prices)
            return s["median"]

        return 0.0

    def find_underpriced(
        self, chars: list[CharacterListing], discount_threshold: float = 0.25
    ) -> list[dict]:
        """Find characters listed below fair value."""
        underpriced = []
        for char in chars:
            if char.price <= 0:
                continue
            fair = self.estimate_fair_value(char)
            if fair <= 0:
                continue
            discount = 1 - (char.price / fair)
            if discount >= discount_threshold:
                underpriced.append({
                    "token_id": char.token_id,
                    "name": char.name,
                    "class_name": char.class_name,
                    "job_name": char.job_name,
                    "level": char.level,
                    "combat_power": char.char_cp or 0,
                    "current_price": char.price,
                    "fair_value": fair,
                    "discount_pct": round(discount * 100, 2),
                    "image_url": char.image_url,
                })
        underpriced.sort(key=lambda x: x["discount_pct"], reverse=True)
        return underpriced


character_price_predictor = CharacterPricePredictor()
