from typing import Dict, Optional
import httpx

# ─── MSU MapleStory N Starforce Probability Tables ──────────────────────────
# Sourced from MSU Dynamic Pricing API (gamestatus/dynamicpricing) and GMS/KMS community data
# Format: current_star -> (success_pct, maintain_pct, degrade_pct, destroy_pct)
# These match standard MapleStory N (Henesys) rates.
STARFORCE_RATES = {
    0:  (0.950, 0.050, 0.000, 0.000),
    1:  (0.900, 0.100, 0.000, 0.000),
    2:  (0.850, 0.150, 0.000, 0.000),
    3:  (0.850, 0.150, 0.000, 0.000),
    4:  (0.800, 0.200, 0.000, 0.000),
    5:  (0.750, 0.250, 0.000, 0.000),
    6:  (0.700, 0.300, 0.000, 0.000),
    7:  (0.650, 0.350, 0.000, 0.000),
    8:  (0.600, 0.400, 0.000, 0.000),
    9:  (0.550, 0.450, 0.000, 0.000),
    10: (0.500, 0.500, 0.000, 0.000),
    11: (0.450, 0.000, 0.550, 0.000),
    12: (0.400, 0.000, 0.594, 0.006),
    13: (0.350, 0.000, 0.637, 0.013),
    14: (0.300, 0.000, 0.686, 0.014),
    # Star 15 is a checkpoint: on fail → maintain (no degradation)
    15: (0.300, 0.700, 0.000, 0.000),   # Note: MSU N - 0% destroy at 15
    16: (0.300, 0.000, 0.679, 0.021),
    17: (0.300, 0.000, 0.679, 0.021),
    18: (0.300, 0.000, 0.672, 0.028),
    19: (0.300, 0.000, 0.672, 0.028),
    # Star 20 is also a checkpoint
    20: (0.300, 0.700, 0.000, 0.000),   # MSU N - 0% destroy at 20
    21: (0.300, 0.000, 0.679, 0.021),
    22: (0.030, 0.000, 0.776, 0.194),
    23: (0.020, 0.000, 0.686, 0.294),
    24: (0.010, 0.000, 0.594, 0.396),
}

# ────────────────────────────────────────────────────────────────────────────
# Cube Tier-up Rates (from community research on MapleStory N rates)
# These match the rates shown in the MSU gamestatus page JS bundle
# Red Cube: Epic→Unique 1.8%, Unique→Legendary 0.3%
# Black Cube: Epic→Unique 3.5%, Unique→Legendary 1.0%
# ────────────────────────────────────────────────────────────────────────────
CUBE_RATES: Dict[str, Dict[str, float]] = {
    "Occult":      {"RareToEpic": 0.009901},
    "Red":         {"RareToEpic": 0.060, "EpicToUnique": 0.018, "UniqueToLegendary": 0.003},
    "Black":       {"RareToEpic": 0.150, "EpicToUnique": 0.035, "UniqueToLegendary": 0.010},
    "BonusOccult": {"RareToEpic": 0.004},
    "Additional":  {"RareToEpic": 0.0476, "EpicToUnique": 0.019, "UniqueToLegendary": 0.005},
}

# Average probability to hit specific common stat goals (placeholder based on community averages)
# Units: Probability per cube attempt at LEGENDARY tier
STAT_GOAL_PROBS = {
    "Red": {
        "2L_BOSS": 0.0125,      # ~80 cubes
        "3L_BOSS": 0.00045,    # ~2200 cubes
        "2L_MAIN_STAT": 0.035, # ~28 cubes
        "3L_MAIN_STAT": 0.0035, # ~285 cubes
        "DROP_RATE": 0.02,     # ~50 cubes
    },
    "Black": {
        "2L_BOSS": 0.022,      # Better prime line rates
        "3L_BOSS": 0.0009,
        "2L_MAIN_STAT": 0.05,
        "3L_MAIN_STAT": 0.007,
    },
    "Additional": {
        "2L_ATTACK": 0.015,
        "2L_MAIN_STAT": 0.03,
    }
}

POTENTIAL_TIERS = ["Normal", "Rare", "Epic", "Unique", "Legendary"]

# ────────────────────────────────────────────────────────────────────────────
# MSU Open API - Enhancement Dynamic Pricing
# Endpoint: GET /v1rc1/enhancement/items/{itemId}/dynamicprice
# ────────────────────────────────────────────────────────────────────────────
_DYNAMIC_PRICING_CACHE: Dict[str, dict] = {}

def _fetch_dynamic_pricing(item_id: int) -> Optional[dict]:
    if str(item_id) in _DYNAMIC_PRICING_CACHE:
        return _DYNAMIC_PRICING_CACHE[str(item_id)]
    try:
        from config import get_settings
        settings = get_settings()
        url = f"{settings.MSU_OPENAPI_BASE}/enhancement/items/{item_id}/dynamicprice"
        r = httpx.get(
            url,
            headers={
                "accept": "application/json",
                "x-nxopen-api-key": settings.MSU_OPENAPI_KEY,
            },
            timeout=10.0,
        )
        if r.status_code == 200:
            body = r.json()
            if body.get("success") and body.get("data"):
                data = body["data"]
                _DYNAMIC_PRICING_CACHE[str(item_id)] = data
                return data
    except Exception:
        pass
    return None


class CalculatorEngine:

    @staticmethod
    def get_sf_cost_from_api(item_id: int, current_star: int) -> Optional[float]:
        """Fetch live Starforce cost per attempt from MSU dynamic pricing API."""
        data = _fetch_dynamic_pricing(item_id)
        if not data:
            return None
        # The dynamic pricing response has starforceInfo.costTable[star] in NESO wei
        star_costs = data.get("starforceInfo", {}).get("costTable", {})
        cost_wei = star_costs.get(str(current_star)) or star_costs.get(current_star)
        if cost_wei:
            try:
                return int(cost_wei) / 1e18
            except (ValueError, TypeError):
                pass
        return None

    @staticmethod
    def calc_sf_cost_per_star(current_star: int, item_level: int = 200) -> float:
        """
        Fallback: estimate Starforce cost per attempt using the MapleStory N base formula.
        Base cost per attempt = 1000 * (star + 1) * (item_level ** 2.7 / 400 + 10)
        Approximation aligned with MSU community calculators.
        """
        cost = 1000 * (current_star + 1) * ((item_level ** 2.7) / 400 + 10)
        return round(cost, 2)

    @staticmethod
    def calc_starforce_ev(
        current_star: int,
        target_star: int,
        cost_per_try: float = 0,
        replace_cost: float = 0,
        item_id: Optional[int] = None,
        item_level: int = 200,
    ) -> float:
        """
        Expected Value in NESO to reach target_star from current_star.
        Uses Markov Chain / linear system solve (value iteration, 200 iterations).
        Checkpoints at star 10, 15, 20 — on failed attempt, star cannot drop below checkpoint.
        Destroy events reset to star 12 (or 0 if below 12).
        """
        if current_star >= target_star:
            return 0.0

        # Build cost table — try live API first, fallback to formula
        cost_table: Dict[int, float] = {}
        for s in range(current_star, target_star):
            if item_id:
                live_cost = CalculatorEngine.get_sf_cost_from_api(item_id, s)
                if live_cost:
                    cost_table[s] = live_cost
                    continue
            if cost_per_try > 0:
                cost_table[s] = cost_per_try
            else:
                cost_table[s] = CalculatorEngine.calc_sf_cost_per_star(s, item_level)

        CHECKPOINTS = {10, 15, 20}
        E: Dict[int, float] = {target_star: 0.0}

        # Initial guess
        for i in range(target_star):
            E[i] = cost_table.get(i, cost_per_try) * (target_star - i) * 3

        # Value iteration — 200 rounds for convergence
        for _ in range(200):
            for i in range(target_star - 1, current_star - 1, -1):
                rates = STARFORCE_RATES.get(i, (0.0, 1.0, 0.0, 0.0))
                p_succ, p_maint, p_drop, p_dest = rates
                c = cost_table.get(i, cost_per_try)

                # Checkpoints: degradation becomes maintain
                drop_to = max(0, i - 1)
                if i in CHECKPOINTS:
                    p_maint += p_drop
                    p_drop = 0.0

                # Destroy resets to star 12 (or 0 if current < 12)
                dest_reset = 12 if i > 12 else 0

                if (1 - p_maint) <= 1e-9:
                    E[i] = float('inf')
                    continue

                E[i] = (
                    c
                    + p_succ * E.get(i + 1, 0.0)
                    + p_drop * E.get(drop_to, 0.0)
                    + p_dest * (replace_cost + E.get(dest_reset, 0.0))
                ) / (1 - p_maint)

        return E.get(current_star, 0.0)

    @staticmethod
    def calc_cube_ev(
        current_tier: str,
        target_tier: str,
        cube_type: str,
        cost_per_cube: float,
        stat_goal: Optional[str] = None,
    ) -> float:
        """
        Expected cube cost (in NESO) to upgrade potential from current_tier to target_tier,
        and optionally hit a specific stat_goal at the target_tier.
        """
        if current_tier not in POTENTIAL_TIERS or target_tier not in POTENTIAL_TIERS:
            return 0.0

        idx_curr = POTENTIAL_TIERS.index(current_tier)
        idx_tgt = POTENTIAL_TIERS.index(target_tier)
        
        total_ev = 0.0
        
        # 1. Tier-up cost
        if idx_curr < idx_tgt:
            rates = CUBE_RATES.get(cube_type, {})
            tier_rate_keys = ["RareToEpic", "EpicToUnique", "UniqueToLegendary"]
            for i in range(idx_curr, idx_tgt):
                if i == 0:
                    total_ev += cost_per_cube # Normal -> Rare usually 100% with scroll
                elif i < 4:
                    key = tier_rate_keys[i - 1]
                    rate = rates.get(key, 0.0)
                    if rate > 0:
                        total_ev += (1.0 / rate) * cost_per_cube

        # 2. Stat goal cost (only calculated at the target tier)
        if stat_goal and stat_goal in STAT_GOAL_PROBS.get(cube_type, {}):
            prob = STAT_GOAL_PROBS[cube_type][stat_goal]
            total_ev += (1.0 / prob) * cost_per_cube

        return total_ev

    @staticmethod
    def estimate_cp_gain(
        old_stats: Dict[str, float],
        new_stats: Dict[str, float],
        base_cp: int,
    ) -> int:
        """
        Estimates new character CP using the CombatPowerEngine.
        Uses percentage scaling methodology (mirrors MapleSprout).
        """
        from services.combat_power_engine import combat_power_engine

        result = combat_power_engine.estimate_upgrade_cp(old_stats, new_stats, base_cp)
        return result["estimated_new_cp"]

    @staticmethod
    def get_simulation_summary(
        current_star: int,
        target_star: int,
        current_potential: str,
        target_potential: str,
        cube_type: str,
        old_stats: Dict[str, float],
        new_stats: Dict[str, float],
        base_cp: int,
        cost_per_try: float = 0,
        replace_cost: float = 0,
        cost_per_cube: float = 0,
        item_id: Optional[int] = None,
        item_level: int = 200,
        # Bonus Potential
        current_bp: Optional[str] = None,
        target_bp: Optional[str] = None,
        bp_cube_type: Optional[str] = "Additional",
        cost_per_bp_cube: float = 0,
        # Stat Goals
        primary_stat_goal: Optional[str] = None,
        bonus_stat_goal: Optional[str] = None,
    ) -> dict:
        """Top-level simulation: returns full cost breakdown and CP estimate."""
        sf_cost = 0.0
        if target_star > current_star:
            sf_cost = CalculatorEngine.calc_starforce_ev(
                current_star, target_star, cost_per_try, replace_cost, item_id, item_level
            )

        cube_cost = 0.0
        if (target_potential != current_potential or primary_stat_goal) and cube_type:
            cube_cost = CalculatorEngine.calc_cube_ev(
                current_potential, target_potential, cube_type, cost_per_cube, primary_stat_goal
            )
            
        bp_cost = 0.0
        if current_bp and target_bp and (target_bp != current_bp or bonus_stat_goal) and bp_cube_type:
            bp_cost = CalculatorEngine.calc_cube_ev(
                current_bp, target_bp, bp_cube_type, cost_per_bp_cube, bonus_stat_goal
            )

        new_cp = CalculatorEngine.estimate_cp_gain(old_stats, new_stats, base_cp)

        # Per star breakdown
        sf_breakdown = {}
        for s in range(current_star, target_star):
            rates = STARFORCE_RATES.get(s, (0, 1, 0, 0))
            trial_cost = CalculatorEngine.calc_sf_cost_per_star(s, item_level) if cost_per_try <= 0 else cost_per_try
            expected_tries = 1.0 / rates[0] if rates[0] > 0 else float("inf")
            sf_breakdown[f"{s}→{s+1}"] = {
                "success_rate": f"{rates[0]*100:.1f}%",
                "expected_tries": round(expected_tries, 1),
                "expected_cost": round(expected_tries * trial_cost),
            }

        return {
            "expected_sf_cost": round(sf_cost),
            "expected_cube_cost": round(cube_cost),
            "expected_bp_cost": round(bp_cost),
            "total_expected_cost": round(sf_cost + cube_cost + bp_cost),
            "estimated_new_cp": new_cp,
            "cp_gain": new_cp - base_cp,
            "cp_gain_pct": round((new_cp - base_cp) / base_cp * 100, 2) if base_cp > 0 else 0,
            "sf_breakdown": sf_breakdown,
        }


calculator_engine = CalculatorEngine()
