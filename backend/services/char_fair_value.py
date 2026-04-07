"""
Character Fair Value Engine — v3

Components:
1. Recent sales (CharacterSaleHistory via RPC OrderMatched) — base comparables
2. Arcane symbol value — cada nível de arcane tem preço
3. Equipment value — starforce + potential + bonus_potential via rarity_engine
4. Ability premium — grades dos 3 slots de ability

O fair value é construído a partir de:
  - Base = mediana de vendas similares (mesma classe, ±20 level)
  - + Valor total dos arcane symbols (por force level)
  - + Valor dos equipamentos mintable (SF + pot + bpot)
  - + Premium de abilities
"""

import json
from statistics import median
from typing import Optional

from sqlalchemy import select, func

from db.database import async_session, CharacterMarketStatus, CharacterSaleHistory
from services.rarity_engine import rarity_engine


# ── Arcane Symbol Pricing ─────────────────────────────────────────
# Cada arcane symbol dá arcaneForce por level.
# O preço é extraído do mercado de arcane symbols reais.
# Arcane Force total → valor estimado em NESO.
# Estes valores são estimativas baseadas em preços de mercado de
# arcane symbols vendidos individualmente no marketplace.

# Simpler: map arcane_force total → valor estimado
# Baseado em preços do marketplace por arcane symbol individual
ARCANE_VALUE_PER_FORCE = 50_000  # ~50k NESO per arcane force
# Bônus por set completo (mais de 18 slots preenchidos):
ARCANE_FULL_BONUS = 1.25  # 25% bonus for full set (390+ force = 26x15)


# ── Ability Premium ────────────────────────────────────────────────

def get_ability_premium(ability_total: int) -> float:
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


# ── Equipment Value via Rarity Engine ─────────────────────────────

# Valores baseados em preços reais do marketplace:
# - Starforce: cada ponto tem custo crescente, em média ~50k-100k NESO por SF
# - Potential: grade 2=Epic~1M, 3=Unique~5M, 4=Legendary~20M
# - Bonus potential: similar mas ~60% do valor

SF_VALUE_PER_POINT = 75_000  # médio por SF point no equipamento

POTENTIAL_VALUES = {
    0: 0,
    1: 100_000,     # Rare
    2: 1_000_000,   # Epic
    3: 5_000_000,   # Unique
    4: 20_000_000,  # Legendary
    5: 50_000_000,  # Special
    6: 100_000_000, # Mythic
}


def compute_item_value(starforce: int, potential_grade: int,
                       bonus_potential=None) -> int:
    """Valor aproximado de um item mintable em NESO."""
    value = 0
    # Starforce
    value += starforce * SF_VALUE_PER_POINT

    # Potential
    pg = min(max(potential_grade, 0), 6)
    value += POTENTIAL_VALUES.get(pg, 0)

    # Bonus potential
    if bonus_potential and isinstance(bonus_potential, dict):
        b_grade = bonus_potential.get("option1", {}).get("grade", 0) or 0
        b_grade = min(max(b_grade, 0), 6)
        # Bonus potential vale ~60% do potential base
        value += int(POTENTIAL_VALUES.get(b_grade, 0) * 0.6)

    return value


def compute_equipment_value(equipped_items: list) -> tuple[int, float]:
    """
    Returns (total_item_value, gear_score).
    Equipment items from the character's equipped_items_json.
    """
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
    """
    Calcula valor estimado dos arcane symbols de um character.
    Cada ponto de arcane force tem um valor de mercado.
    Bonus para set completo.
    """
    if arcane_force <= 0:
        return 0

    base_value = arcane_force * ARCANE_VALUE_PER_FORCE

    # Bonus por set completo (26 slots, cada dando 15 force = 390 total)
    # Se tem arcane_force próximo do máximo, bonus
    if arcane_force >= 350:  # Set eterno completo
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
    Compute fair value:
    1. Find comparable recent sales (local DB, captured via RPC OrderMatched)
    2. Use median as base
    3. Add arcane symbol value
    4. Add equipment item value
    5. Apply ability premium
    """
    breakdown = {}

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

    # === 2. Comparable listings (DB enriched) ===
    listing_prices = []
    if sales_median <= 0:
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
                listing_prices = [r.price for r in rows]
                listing_median = median(listing_prices)
                sales_median = listing_median
                breakdown["listing_count"] = len(listing_prices)

    # === 3. Determine base value ===
    if sales_median and sales_median > 0:
        base_value = sales_median
        confidence = "high" if len(sales_prices) >= 5 else "medium"
    else:
        # No comparable data — return 0, don't invent
        return 0, "none", json.dumps({"reason": "no_comparable_data", "class": cls_name})

    breakdown["base_median"] = round(base_value, 2)

    # === 4. Arcane value — ADDED to base (not multiplied) ===
    arcane_value = compute_arcane_value(arcane_force)
    breakdown["arcane_force"] = arcane_force
    breakdown["arcane_tier"] = arcane_tier
    breakdown["arcane_value"] = arcane_value

    # === 5. Equipment value ===
    equip_value = 0
    if equipped_item_ids:
        equip_value, gear_score_final = compute_equipment_value(equipped_item_ids)
        gear_score = gear_score_final if gear_score_final > 0 else gear_score
    breakdown["equipment_value"] = equip_value

    # === 6. Ability premium (percentage of base) ===
    ability_pct = get_ability_premium(ability_total)
    ability_adj = base_value * ability_pct
    breakdown["ability_total"] = ability_total
    breakdown["ability_pct"] = round(ability_pct * 100, 1)
    breakdown["ability_adjustment"] = round(ability_adj, 2)

    # === FINAL: base + arcane + equipment + ability premium ===
    final = base_value + arcane_value + equip_value + ability_adj

    # Sanity cap: can't be more than 4x the median
    final = min(final, base_value * 4.0)
    # Floor: at least 0.7x base
    final = max(final, base_value * 0.7)

    breakdown["final"] = round(final, 2)
    breakdown["confidence"] = confidence

    return round(final, 2), confidence, json.dumps(breakdown)


# ── Refresh Loop ──────────────────────────────────────────────────

async def refresh_all_fair_values():
    """Recompute fair values for all enriched listings."""
    from sqlalchemy import select

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
