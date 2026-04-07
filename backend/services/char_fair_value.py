"""
Character Fair Value Engine — v4

Fair value depends on character level bracket:
- <200: NO arcane symbols or V-skills → fair value = level-based median
       from comparable listings (same class, same level bracket)
- 200+: HAS arcane + V-skills → fair value = sales/comparable base
       + arcane value + equipment value + ability premium

Components for 200+:
1. Recent sales (CharacterSaleHistory via RPC OrderMatched) — base comparables
2. Arcane symbol value — each force level has a price
3. Equipment value — starforce + potential + bonus_potential
4. Ability premium — grades dos 3 slots de ability
"""

import json
from statistics import median
from typing import Optional

from sqlalchemy import select, func

from db.database import async_session, CharacterMarketStatus, CharacterSaleHistory


# ── Arcane Symbol Pricing ─────────────────────────────────────────
# Arcane force → estimated NESO value
# Based on marketplace prices of individual arcane symbols
ARCANE_VALUE_PER_FORCE = 50_000  # ~50k NESO per arcane force point
ARCANE_FULL_BONUS = 1.25  # 25% bonus for complete set (350+ force)


# ── Ability Premium ────────────────────────────────────────────────

def get_ability_premium(ability_total: int) -> float:
    """Premium percentage for ability grades."""
    if ability_total >= 18:
        return 0.90
    if ability_total >= 16:
        return 0.70
    if ability_total >= 14:
        return 0.50
    if ability_total >= 12:
        return 0.35
    if ability_total >= 10:
        return 0.20
    if ability_total >= 8:
        return 0.10
    if ability_total >= 4:
        return 0.03
    return 0.00


# ── Equipment Value ───────────────────────────────────────────────

SF_VALUE_PER_POINT = 75_000  # ~75k per SF point

POTENTIAL_VALUES = {
    0: 0,
    1: 100_000,       # Rare
    2: 1_000_000,     # Epic
    3: 5_000_000,     # Unique
    4: 20_000_000,    # Legendary
    5: 50_000_000,    # Special
    6: 100_000_000,   # Mythic
}


def compute_item_value(starforce: int, potential_grade: int,
                       bonus_potential=None) -> int:
    """Estimated value of a mintable item in NESO."""
    value = 0
    value += starforce * SF_VALUE_PER_POINT

    pg = min(max(potential_grade, 0), 6)
    value += POTENTIAL_VALUES.get(pg, 0)

    if bonus_potential and isinstance(bonus_potential, dict):
        b_grade = bonus_potential.get("option1", {}).get("grade", 0) or 0
        b_grade = min(max(b_grade, 0), 6)
        value += int(POTENTIAL_VALUES.get(b_grade, 0) * 0.6)

    return value


def compute_equipment_value(equipped_items: list) -> tuple[int, float]:
    """Returns (total_item_value, avg_gear_score)."""
    total_value = 0
    gear_scores = []

    for eq in equipped_items:
        sf = eq.get("starforce", 0) or 0
        pg = eq.get("potential_grade", 0) or 0
        bp = eq.get("bonus_potential")

        item_val = compute_item_value(sf, pg, bp)
        total_value += item_val

        if eq.get("token_id"):  # Only mintable items
            quality = (sf * 4) + (pg * 10) + ((bp or {}).get("option1", {}).get("grade", 0) or 0) * 5
            gear_scores.append(quality)

    avg_gear = sum(gear_scores) / max(len(gear_scores), 1) if gear_scores else 0
    return total_value, round(avg_gear, 2)


# ── Arcane Value ──────────────────────────────────────────────────

def compute_arcane_value(arcane_force: int) -> int:
    """Estimated value of arcane symbols in NESO."""
    if arcane_force <= 0:
        return 0

    base_value = arcane_force * ARCANE_VALUE_PER_FORCE

    # Complete set bonus (26 slots × 15 force = 390 total)
    if arcane_force >= 350:
        base_value = int(base_value * ARCANE_FULL_BONUS)

    return base_value


# ── Core Fair Value computation ───────────────────────────────────

async def compute_char_fair_value(
    cls_name: str, level: int, arcane_tier: str,
    ability_total: int, gear_score: float,
    arcane_force: int = 0,
    equipped_item_ids: list[dict] = None,
) -> tuple[float, str, str]:
    """
    Compute fair value with level-aware strategy:

    <200: No arcane/V-skill → use level-based comparable median from current listings
    200+: Full computation → base from sales + arcane + equipment + ability
    """
    breakdown = {}
    is_high_level = level >= 200

    # === 1. Comparable sales (local DB from RPC watcher) ===
    sales_prices = []
    async with async_session() as session:
        stmt = select(CharacterSaleHistory).where(
            CharacterSaleHistory.class_name == cls_name,
            CharacterSaleHistory.level >= max(1, level - 20),
            CharacterSaleHistory.level <= level + 20,
        ).order_by(
            CharacterSaleHistory.sale_date.desc()
        ).limit(30)
        sales = (await session.execute(stmt)).scalars().all()

        if sales:
            # For 200+ chars: filter by arcane tier similarity
            if is_high_level and arcane_tier:
                sales_filtered = [s for s in sales if s.arcane_force > 0]
                if sales_filtered:
                    sales_prices = [s.price for s in sales_filtered if s.price > 0]
            else:
                sales_prices = [s.price for s in sales if s.price > 0]
            breakdown["local_sales_count"] = len(sales_prices)

    # IQR filter outliers
    if len(sales_prices) >= 4:
        sorted_p = sorted(sales_prices)
        n = len(sorted_p)
        q1 = sorted_p[n // 4]
        q3 = sorted_p[(3 * n) // 4]
        iqr = q3 - q1
        sales_prices = [p for p in sales_prices if q1 - 1.5 * iqr <= p <= q3 + 1.5 * iqr]
        breakdown["local_sales_after_iqr"] = len(sales_prices)

    sales_median = median(sales_prices) if sales_prices else 0

    # === 2. Fallback comparable listings ===
    listing_prices = []
    async with async_session() as session:
        stmt = select(CharacterMarketStatus).where(
            CharacterMarketStatus.class_name == cls_name,
            CharacterMarketStatus.status.in_(["enriched", "pending"]),
            CharacterMarketStatus.price > 0,
            CharacterMarketStatus.level >= max(1, level - 20),
            CharacterMarketStatus.level <= level + 20,
        )
        rows = (await session.execute(stmt)).scalars().all()

        if rows:
            # For 200+: only compare to chars with arcane (similar quality)
            if is_high_level and arcane_force > 0:
                rows = [r for r in rows if r.arcane_force > 0]
            listing_prices = [r.price for r in rows if r.price > 0]

            # IQR filter listings too
            if len(listing_prices) >= 4:
                sorted_lp = sorted(listing_prices)
                n2 = len(sorted_lp)
                q1l = sorted_lp[n2 // 4]
                q3l = sorted_lp[(3 * n2) // 4]
                iqrl = q3l - q1l
                listing_prices = [p for p in listing_prices
                                  if q1l - 1.5 * iqrl <= p <= q3l + 1.5 * iqrl]

    if not sales_median or sales_median <= 0:
        if listing_prices:
            listing_median = median(listing_prices)
            if listing_median > 0:
                base_value = listing_median
                breakdown["fallback_listing_median"] = round(listing_median, 2)
                breakdown["fallback_count"] = len(listing_prices)
                confidence = "low"
            else:
                base_value = 0
                confidence = "none"
        else:
            base_value = 0
            confidence = "none"
    else:
        base_value = sales_median
        confidence = "high" if len(sales_prices) >= 5 else "medium"

    # === For chars <200: base_value comes from level-based comparables ===
    if not is_high_level:
        # <200 chars: base_value is already from comparable listings at same level
        # Add nothing — they have no arcane, no V-skills, no meaningful equipment
        if base_value <= 0:
            return 0, "none", json.dumps({
                "reason": "no_comparable_data",
                "class": cls_name,
                "level": level,
            })

        # Sanity clamp for low-level char fairness
        final = base_value
        final = max(final, base_value * 0.8)
        final = min(final, base_value * 1.25)

        breakdown["strategy"] = "level_based"
        breakdown["final"] = round(final, 2)
        breakdown["confidence"] = confidence
        return round(final, 2), confidence, json.dumps(breakdown)

    # === For chars 200+: full computation ===
    if base_value <= 0:
        return 0, "none", json.dumps({
            "reason": "no_comparable_data_200plus",
            "class": cls_name,
            "level": level,
        })

    breakdown["base_median"] = round(base_value, 2)

    # Arcane value (ADDED to base)
    arcane_value = compute_arcane_value(arcane_force)
    breakdown["arcane_force"] = arcane_force
    breakdown["arcane_tier"] = arcane_tier
    breakdown["arcane_value"] = arcane_value

    # Equipment value
    equip_value = 0
    if equipped_item_ids:
        equip_value, gear_score_final = compute_equipment_value(equipped_item_ids)
        gear_score = gear_score_final if gear_score_final > 0 else gear_score
    breakdown["equipment_value"] = equip_value

    # Ability premium
    ability_pct = get_ability_premium(ability_total)
    ability_adj = base_value * ability_pct
    breakdown["ability_total"] = ability_total
    breakdown["ability_pct"] = round(ability_pct * 100, 1)
    breakdown["ability_adjustment"] = round(ability_adj, 2)

    # FINAL: base + arcane + equipment + ability premium
    final = base_value + arcane_value + equip_value + ability_adj

    # Sanity cap: at most 4x base
    final = min(final, base_value * 4.0)
    # Floor: at least 0.7x base
    final = max(final, base_value * 0.7)

    breakdown["final"] = round(final, 2)
    breakdown["confidence"] = confidence

    return round(final, 2), confidence, json.dumps(breakdown)


# ── Refresh Loop ──────────────────────────────────────────────────

async def refresh_all_fair_values():
    """Recompute fair values for all enriched listings."""
    async with async_session() as session:
        stmt = select(CharacterMarketStatus).where(
            CharacterMarketStatus.status == "enriched"
        )
        rows = (await session.execute(stmt)).scalars().all()

    updated = 0
    for row in rows:
        try:
            equipped_ids = json.loads(row.equipped_item_ids_json) if row.equipped_item_ids_json else []
            fair_value, confidence, breakdown_json = await compute_char_fair_value(
                cls_name=row.class_name,
                level=row.level,
                arcane_tier=row.arcane_set_tier,
                ability_total=row.ability_total,
                gear_score=row.gear_score,
                arcane_force=row.arcane_force,
                equipped_item_ids=equipped_ids,
            )
            row.fair_value = fair_value
            row.confidence = confidence
            row.fair_breakdown = breakdown_json

            async with async_session() as s2:
                s2.add(row)
                await s2.commit()

            updated += 1
        except Exception as e:
            print(f"[FairValue] Error computing for {row.token_id}: {e}")

    print(f"[FairValue] Updated {updated}/{len(rows)} listings")
    return updated
