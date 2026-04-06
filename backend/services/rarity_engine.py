"""
Rarity & Scarcity Engine for MapleStory Universe items.

Computes a Scarcity Score (0-100) by comparing each item's attributes
against the global distribution of all indexed items.

Uses real MSU data structures:
- starforce (0-25)
- potentialGrade / bonusPotentialGrade (0-6)
- category (weapon type, armor slot, etc)
- name frequency (how many copies exist on market)

Fixed: properly distinguishes Legendary (grade 4) from Unique (grade 3)
by widening the multiplier gap and giving bonus potential proper weight.
"""

from collections import Counter, defaultdict
from typing import Optional

from models.item import ItemListing
from models.market import ScarcityScore


class RarityEngine:

    POTENTIAL_GRADES = {
        0: "None", 1: "Rare", 2: "Epic", 3: "Unique",
        4: "Legendary", 5: "Special", 6: "Mythic",
    }

    STARFORCE_MULTIPLIERS = {
        range(0, 5): 1.0, range(5, 10): 1.1, range(10, 15): 1.3,
        range(15, 18): 1.6, range(18, 21): 2.0, range(21, 23): 2.8,
        range(23, 26): 4.0,
    }

    # Grade multipliers: calibrated so grade 3 (Unique) ≠ 4 (Legendary)
    # MSU API conflates these in base pricing, but bonus_potential is the
    # true differentiator. We widen gaps to reflect real rarity.
    POTENTIAL_MULTIPLIERS = {
        0: 1.00, 1: 1.08, 2: 1.20, 3: 1.45,
        4: 2.00, 5: 2.60, 6: 3.50,
    }

    def __init__(self):
        self._items: list[ItemListing] = []
        self._name_counts: Counter = Counter()
        self._category_counts: Counter = Counter()
        self._starforce_distribution: Counter = Counter()
        self._potential_distribution: Counter = Counter()
        self._bonus_potential_distribution: Counter = Counter()
        self._combo_distribution: Counter = Counter()  # (name, sf, pot) combos
        self._total_items: int = 0
        self._price_by_name: dict[str, list[float]] = defaultdict(list)
        self._price_by_combo: dict[str, list[float]] = defaultdict(list)
        # Pre-computed quick scores for ranking
        self._quick_scores: dict[str, float] = {}

    def rebuild_index(self, items: list[ItemListing]):
        """Rebuild the global distribution index from all indexed items."""
        self._items = items
        self._total_items = len(items)
        self._name_counts.clear()
        self._category_counts.clear()
        self._starforce_distribution.clear()
        self._potential_distribution.clear()
        self._bonus_potential_distribution.clear()
        self._combo_distribution.clear()
        self._price_by_name.clear()
        self._price_by_combo.clear()
        self._quick_scores.clear()

        for item in items:
            self._name_counts[item.name] += 1
            self._category_counts[item.category_no] += 1
            self._starforce_distribution[item.starforce] += 1
            self._potential_distribution[item.potential_grade] += 1
            self._bonus_potential_distribution[item.bonus_potential_grade] += 1

            # Track combinations for better fair value: include bonus potential
            combo = f"{item.name}|sf{item.starforce}|p{item.potential_grade}|bp{item.bonus_potential_grade}"
            self._combo_distribution[combo] += 1

            if item.price > 0:
                self._price_by_name[item.name].append(item.price)
                self._price_by_combo[combo].append(item.price)

        # Pre-compute quick scores for all items (used in ranking)
        for item in items:
            self._quick_scores[item.token_id] = self._quick_score(item)

    def _get_starforce_multiplier(self, sf: int) -> float:
        for sf_range, mult in self.STARFORCE_MULTIPLIERS.items():
            if sf in sf_range:
                return mult
        return 5.0

    def _name_rarity(self, name: str) -> float:
        if self._total_items == 0:
            return 0.0
        count = self._name_counts.get(name, 0)
        if count == 0:
            return 1.0
        return 1.0 - (count / self._total_items)

    def _estimate_fair_value(self, item: ItemListing, score: float) -> float:
        """
        Fair value estimation using multiple price references:
        1. Exact combo match (name+sf+potential+bonus_potential) - best
        2. Same name items - fallback
        3. Score adjustment for unique combos
        """
        # Try exact combo first (includes bonus potential for Legendary vs Unique)
        combo = f"{item.name}|sf{item.starforce}|p{item.potential_grade}|bp{item.bonus_potential_grade}"
        prices = self._price_by_combo.get(combo, [])

        if len(prices) < 2:
            # Fall back to name-level pricing
            prices = self._price_by_name.get(item.name, [])

        if not prices:
            return 0.0

        prices_sorted = sorted(prices)
        n = len(prices_sorted)

        # IQR filtering for outliers
        if n >= 4:
            q1 = prices_sorted[n // 4]
            q3 = prices_sorted[(3 * n) // 4]
            iqr = q3 - q1
            filtered = [p for p in prices_sorted if q1 - 1.5 * iqr <= p <= q3 + 1.5 * iqr]
            if filtered:
                prices_sorted = filtered
                n = len(prices_sorted)

        median = prices_sorted[n // 2]

        # Score-based adjustment: higher scarcity = higher fair value
        score_adj = 1.0 + ((score - 50) / 100)
        return median * max(score_adj, 0.3)

    def compute_score(self, item: ItemListing) -> ScarcityScore:
        """
        Compute scarcity score (0-100).

        Components:
        1. Name rarity (15%) - supply of this item name
        2. Starforce rarity (25%) - enhancement level scarcity
        3. Potential grade (20%) - potential tier scarcity
           - Properly distinguishes Unique (3) vs Legendary (4) via wider multiplier gap
        4. Bonus potential (20%) - bonus pot tier scarcity
           - Now weighted higher: bonus potential differentiates otherwise identical items
        5. Combo rarity (20%) - this exact combination
        """
        if self._total_items == 0:
            return ScarcityScore(
                token_id=item.token_id, name=item.name, score=0.0, total_items=0
            )

        breakdown = {}

        # 1. Name rarity
        name_score = self._name_rarity(item.name) * 100
        breakdown["name_rarity"] = round(name_score, 2)
        breakdown["name_supply"] = self._name_counts.get(item.name, 0)

        # 2. Starforce
        sf_count = self._starforce_distribution.get(item.starforce, 0)
        sf_rarity = (1.0 - sf_count / self._total_items) * 100
        sf_mult = self._get_starforce_multiplier(item.starforce)
        sf_score = min(sf_rarity * sf_mult, 100)
        breakdown["starforce_score"] = round(sf_score, 2)
        breakdown["starforce"] = item.starforce

        # 3. Potential grade (weighted 20%)
        pg_count = self._potential_distribution.get(item.potential_grade, 0)
        pg_rarity = (1.0 - pg_count / self._total_items) * 100
        pg_mult = self.POTENTIAL_MULTIPLIERS.get(item.potential_grade, 1.0)
        pg_score = min(pg_rarity * pg_mult, 100)
        breakdown["potential_score"] = round(pg_score, 2)
        breakdown["potential_label"] = self.POTENTIAL_GRADES.get(item.potential_grade, "?")

        # 4. Bonus potential (weighted 20% - increased from 15%)
        # This is the key differentiator: Unique vs Legendary items may have same base grade
        # in the API, but different bonus potential stats.
        bpg_count = self._bonus_potential_distribution.get(item.bonus_potential_grade, 0)
        bpg_rarity = (1.0 - bpg_count / self._total_items) * 100
        bpg_mult = self.POTENTIAL_MULTIPLIERS.get(item.bonus_potential_grade, 1.0)
        bpg_score = min(bpg_rarity * bpg_mult, 100)
        breakdown["bonus_potential_score"] = round(bpg_score, 2)
        breakdown["bonus_potential_label"] = self.POTENTIAL_GRADES.get(item.bonus_potential_grade, "None")

        # 5. Combo rarity (includes bonus potential in combo key)
        combo = f"{item.name}|sf{item.starforce}|p{item.potential_grade}|bp{item.bonus_potential_grade}"
        combo_count = self._combo_distribution.get(combo, 0)
        combo_rarity = (1.0 - combo_count / self._total_items) * 100
        breakdown["combo_rarity"] = round(combo_rarity, 2)
        breakdown["combo_supply"] = combo_count

        # Weighted final: bonus potential now 20% (was 15%)
        final = (
            name_score * 0.15
            + sf_score * 0.25
            + pg_score * 0.20
            + bpg_score * 0.20
            + combo_rarity * 0.20
        )
        final = max(0, min(100, final))

        # Rank using pre-computed scores
        rank = sum(1 for s in self._quick_scores.values() if s > final) + 1
        percentile = ((self._total_items - rank) / self._total_items * 100) if self._total_items else 0

        fair_value = self._estimate_fair_value(item, final)

        return ScarcityScore(
            token_id=item.token_id,
            name=item.name,
            score=round(final, 2),
            rank=rank,
            total_items=self._total_items,
            percentile=round(percentile, 2),
            breakdown=breakdown,
            fair_value_estimate=round(fair_value, 2),
        )

    def _quick_score(self, item: ItemListing) -> float:
        """Fast score for ranking."""
        n = self._name_rarity(item.name) * 100 * 0.15
        sf_c = self._starforce_distribution.get(item.starforce, 0)
        sf = min((1 - sf_c / max(self._total_items, 1)) * 100 * self._get_starforce_multiplier(item.starforce), 100) * 0.25
        pg_c = self._potential_distribution.get(item.potential_grade, 0)
        pg = min((1 - pg_c / max(self._total_items, 1)) * 100 * self.POTENTIAL_MULTIPLIERS.get(item.potential_grade, 1.0), 100) * 0.20
        bpg_c = self._bonus_potential_distribution.get(item.bonus_potential_grade, 0)
        bpg = min((1 - bpg_c / max(self._total_items, 1)) * 100 * self.POTENTIAL_MULTIPLIERS.get(item.bonus_potential_grade, 1.0), 100) * 0.20
        combo = f"{item.name}|sf{item.starforce}|p{item.potential_grade}|bp{item.bonus_potential_grade}"
        cc = self._combo_distribution.get(combo, 0)
        cr = (1 - cc / max(self._total_items, 1)) * 100 * 0.20
        return n + sf + pg + bpg + cr

    def find_underpriced(
        self, items: list[ItemListing], discount_threshold: float = 0.30
    ) -> list[dict]:
        """Find items listed below fair value."""
        underpriced = []
        for item in items:
            if item.price <= 0:
                continue
            score = self.compute_score(item)
            if score.fair_value_estimate <= 0:
                continue
            discount = 1 - (item.price / score.fair_value_estimate)
            if discount >= discount_threshold:
                underpriced.append({
                    "token_id": item.token_id,
                    "name": item.name,
                    "current_price": item.price,
                    "fair_value": score.fair_value_estimate,
                    "discount_pct": round(discount * 100, 2),
                    "scarcity_score": score.score,
                    "starforce": item.starforce,
                    "potential_grade": item.potential_grade,
                    "bonus_potential_grade": item.bonus_potential_grade,
                    "potential_label": self.POTENTIAL_GRADES.get(item.potential_grade, "?"),
                    "bonus_potential_label": self.POTENTIAL_GRADES.get(item.bonus_potential_grade, "None"),
                    "category_label": item.category_label,
                    "listed_at": str(item.created_at) if item.created_at else None,
                    "image_url": item.image_url,
                })
        underpriced.sort(key=lambda x: x["discount_pct"], reverse=True)
        return underpriced


# Singleton
rarity_engine = RarityEngine()
