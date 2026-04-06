from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

from services.calculator_engine import calculator_engine, POTENTIAL_TIERS, CUBE_RATES, STARFORCE_RATES
from services.combat_power_engine import (
    combat_power_engine,
    get_sf_stat_gain,
    SF_ARMOR_STAT,
    SF_WEAPON_ATT,
    SF_ARMOR_ATT_BONUS,
    _get_level_bracket,
)
from services.legion_bonus import calculate_legion_bonus, get_legion_tier_milestones
from services.collection_bonus import calculate_collection_bonus, get_collection_milestones

router = APIRouter(prefix="/api/calculator", tags=["calculator"])


class SimulationRequest(BaseModel):
    base_cp: int

    old_stats: Dict[str, float]
    new_stats: Dict[str, float]

    # Starforce
    current_sf: int = 0
    target_sf: int = 0
    sf_cost_per_try: float = 0.0
    sf_replace_cost: float = 0.0
    item_id: Optional[int] = None
    item_level: int = 200

    # Item type for CP calculation
    item_type: str = "armor"  # "weapon" | "armor" | "accessory"

    # Potential
    current_potential: str = "Normal"
    target_potential: str = "Normal"
    cube_type: str = "Red"
    cube_cost: float = 0.0
    primary_stat_goal: Optional[str] = None

    # Bonus Potential (Additional)
    current_bp: Optional[str] = "Normal"
    target_bp: Optional[str] = "Normal"
    bp_cube_type: Optional[str] = "Additional"
    bp_cube_cost: float = 0.0
    bonus_stat_goal: Optional[str] = None

    # Character stats for SF CP upgrade calculation
    char_stats: Optional[Dict[str, float]] = None

    # Legion & Collection bonuses
    legion_blocks: int = 0
    collection_score: int = 0


class SfCpUpgradeRequest(BaseModel):
    """Request for precise Combat Rating Upgrade calculation using SF stat tables."""
    base_cp: int
    char_stats: Dict[str, float]  # Full character stat profile
    item_level: int = 200
    from_star: int = 0
    to_star: int = 22
    item_type: str = "armor"  # "weapon" | "armor"


class SfStatPreviewRequest(BaseModel):
    """Request for per-star stat preview (what stats each star gives)."""
    item_level: int
    from_star: int = 0
    to_star: int = 22
    item_type: str = "armor"


@router.post("/estimate")
async def estimate_simulation(req: SimulationRequest):
    """
    Full simulation endpoint — returns EV costs, CP estimate, and a per-star cost breakdown.
    Uses live MSU Dynamic Pricing if item_id is provided, else formula / manual cost.

    Now includes sf_cp_upgrade (Combat Rating Upgrade) when char_stats is provided.
    """
    result = calculator_engine.get_simulation_summary(
        current_star=req.current_sf,
        target_star=req.target_sf,
        current_potential=req.current_potential,
        target_potential=req.target_potential,
        cube_type=req.cube_type,
        old_stats=req.old_stats,
        new_stats=req.new_stats,
        base_cp=req.base_cp,
        cost_per_try=req.sf_cost_per_try,
        replace_cost=req.sf_replace_cost,
        cost_per_cube=req.cube_cost,
        item_id=req.item_id,
        item_level=req.item_level,
        # Bonus Potential
        current_bp=req.current_bp,
        target_bp=req.target_bp,
        bp_cube_type=req.bp_cube_type,
        cost_per_bp_cube=req.bp_cube_cost,
        # Stat Goals
        primary_stat_goal=req.primary_stat_goal,
        bonus_stat_goal=req.bonus_stat_goal,
    )

    # If char_stats provided, enhance with precise SF CP upgrade calculation
    if req.char_stats and req.base_cp > 0 and req.target_sf > req.current_sf:
        try:
            sf_cp = combat_power_engine.calculate_sf_cp_delta(
                char_stats=req.char_stats,
                real_cp=req.base_cp,
                item_level=req.item_level,
                from_star=req.current_sf,
                to_star=req.target_sf,
                item_type=req.item_type,
            )
            result["sf_cp_upgrade"] = sf_cp
            # Override the generic cp_gain with the SF-precise one
            result["cp_gain"] = sf_cp.get("cp_gain", result.get("cp_gain", 0))
            result["cp_gain_pct"] = sf_cp.get("cp_gain_pct", result.get("cp_gain_pct", 0))
            result["estimated_new_cp"] = sf_cp.get("estimated_new_cp", req.base_cp)
        except Exception as e:
            result["sf_cp_upgrade_error"] = str(e)

    # Legion & Collection bonus computation
    if req.legion_blocks > 0:
        result["legion_bonus"] = calculate_legion_bonus(req.legion_blocks)

    if req.collection_score > 0:
        result["collection_bonus"] = calculate_collection_bonus(req.collection_score)

    return result


@router.post("/sf-cp-upgrade")
async def calculate_sf_cp_upgrade(req: SfCpUpgradeRequest):
    """
    Dedicated endpoint for Combat Rating Upgrade calculation.

    Returns a precise estimate of how much CP the character will gain
    from starforcing an item from `from_star` to `to_star`.

    Uses the per-item-level SF stat gain tables (community-verified).
    """
    if req.base_cp <= 0:
        raise HTTPException(400, "base_cp must be > 0")
    if req.from_star >= req.to_star:
        raise HTTPException(400, "from_star must be < to_star")
    if not req.char_stats:
        raise HTTPException(400, "char_stats required")

    result = combat_power_engine.calculate_sf_cp_delta(
        char_stats=req.char_stats,
        real_cp=req.base_cp,
        item_level=req.item_level,
        from_star=req.from_star,
        to_star=req.to_star,
        item_type=req.item_type,
    )
    return result


@router.post("/sf-stat-preview")
async def get_sf_stat_preview(req: SfStatPreviewRequest):
    """
    Returns the per-star stat preview for an item at a given level.
    Useful for showing "+5 STR, +2 ATT" per star in the UI.
    """
    is_weapon = req.item_type.lower() == "weapon"
    bracket = _get_level_bracket(req.item_level)

    if not bracket:
        return {"error": "Item level not in supported range (130-299)", "stars": []}

    armor_tbl = SF_ARMOR_STAT.get(bracket, [])
    att_tbl = (SF_WEAPON_ATT if is_weapon else SF_ARMOR_ATT_BONUS).get(bracket, [])

    stars = []
    cum_stat = 0
    cum_att = 0
    for star in range(min(req.to_star, 25)):
        s = armor_tbl[star] if star < len(armor_tbl) else 0
        a = att_tbl[star] if star < len(att_tbl) else 0
        cum_stat += s
        cum_att += a
        if star >= req.from_star:
            stars.append({
                "from_star": star,
                "to_star": star + 1,
                "stat_gain": s,
                "att_gain": a,
                "cumulative_stat": cum_stat,
                "cumulative_att": cum_att,
            })

    total = get_sf_stat_gain(req.item_level, req.from_star, req.to_star, is_weapon=is_weapon)
    return {
        "item_level": req.item_level,
        "item_type": req.item_type,
        "bracket": list(bracket),
        "from_star": req.from_star,
        "to_star": req.to_star,
        "total_stat_gain": total["primary_stat"],
        "total_att_gain": total["att"],
        "stars": stars,
    }


@router.get("/rates/starforce")
async def get_starforce_rates():
    """Return the full Starforce probability table used in simulations."""
    table = []
    for star, (p_succ, p_maint, p_drop, p_dest) in STARFORCE_RATES.items():
        table.append({
            "star": star,
            "success_pct": round(p_succ * 100, 1),
            "maintain_pct": round(p_maint * 100, 1),
            "degrade_pct": round(p_drop * 100, 1),
            "destroy_pct": round(p_dest * 100, 1),
            "is_checkpoint": star in {10, 15, 20},
        })
    return {"rates": table}


@router.get("/rates/cubes")
async def get_cube_rates():
    """Return cube tier-up probability table."""
    return {
        "tiers": POTENTIAL_TIERS,
        "rates": {
            cube: {
                "EpicToUnique": data.get("EpicToUnique", 0),
                "UniqueToLegendary": data.get("UniqueToLegendary", 0),
                "avg_cubes_epic_to_legendary": round(
                    (1 / data["EpicToUnique"] if data.get("EpicToUnique") else 0)
                    + (1 / data["UniqueToLegendary"] if data.get("UniqueToLegendary") else 0),
                    1
                )
            }
            for cube, data in CUBE_RATES.items()
        }
    }


@router.post("/legion-preview")
async def legion_preview(blocks: int = 0):
    """Preview legion bonuses for a given block count."""
    return {
        "bonuses": calculate_legion_bonus(blocks),
        "milestones": get_legion_tier_milestones(),
    }


@router.post("/collection-preview")
async def collection_preview(score: int = 0):
    """Preview collection bonuses for a given score."""
    return {
        "bonuses": calculate_collection_bonus(score),
        "milestones": get_collection_milestones(),
    }
