"""
CP Engine verification test.

Tests the Combat Power calculation against known real values from the MSU API.
MSU API field `apStat.attackPower` IS the real Combat Power (전투력).
"""
import json
from services.combat_power_engine import CombatPowerEngine, _calc_set_bonus_cp

result_data = {}

# ─── Test 1: Set bonus calculations ─────────────────────────────────────────
result_data["Arcane Umbra 8pc"] = _calc_set_bonus_cp('Arcane Umbra', 8, 5_000_000)
result_data["Arcane Umbra 7pc"] = _calc_set_bonus_cp('Arcane Umbra', 7, 5_000_000)
result_data["Genesis 8pc"] = _calc_set_bonus_cp('Genesis', 8, 12_000_000)

# ─── Test 2: Wind Archer Lv80 (real data from char_detail_sample.json) ──────
# Real CP from API: attackPower = "1897"
wind_archer_stats = {
    "str":               {"total": 57,  "base": 4,   "enhance": 53},
    "dex":               {"total": 528, "base": 413, "enhance": 115},
    "int":               {"total": 18,  "base": 4,   "enhance": 14},
    "luk":               {"total": 18,  "base": 4,   "enhance": 14},
    "pad":               {"total": 125, "base": 125, "enhance": 0},
    "mad":               {"total": 1,   "base": 1,   "enhance": 0},
    "damage":            {"total": 0,   "base": 0,   "enhance": 0},
    "bossMonsterDamage": {"total": 0,   "base": 0,   "enhance": 0},
    "criticalDamage":    {"total": 0,   "base": 0,   "enhance": 0},
    "attackPower": "1897",
}

wa_char_stats = CombatPowerEngine.extract_stats_from_character(wind_archer_stats, "Wind Archer")
wa_calc_cp = CombatPowerEngine.calculate_cp(
    primary_stat=wa_char_stats["primary_stat"],
    secondary_stat=wa_char_stats["secondary_stat"],
    total_att=125,  # pad.total
    damage_pct=0,
    boss_damage_pct=0,
    crit_damage_pct=0,
    crit_damage_base=0,
)
result_data["wind_archer_lv80"] = {
    "real_cp": 1897,
    "calc_cp": round(wa_calc_cp),
    "primary": wa_char_stats["primary_stat"],
    "secondary": wa_char_stats["secondary_stat"],
    "error_pct": round(abs(wa_calc_cp - 1897) / 1897 * 100, 2),
}

# ─── Test 3: Bowmaster 5M CP (realistic stats) ─────────────────────────────
# Bowmaster: primary=DEX, secondary=STR
ap_stats = {
    "dex":               {"total": 30000, "base": 4,   "enhance": 29996},
    "str":               {"total": 2500,  "base": 4,   "enhance": 2496},
    "pad":               {"total": 1200,  "base": 100, "enhance": 1100},
    "damage":            {"total": 60,    "base": 0,   "enhance": 60},
    "bossMonsterDamage": {"total": 230,   "base": 0,   "enhance": 230},
    "criticalDamage":    {"total": 50,    "base": 35,  "enhance": 15},
    "attackPower": "5000000",  # This IS the real CP, not ATT
}

items = [
    {
        "slot": "weapon", "item_type": "equip",
        "name": "Arcane Umbra Bow", "starforce": 22,
        "potential": {"option1": {"label": "ATT +12%"}},
        "bonus_potential": {},
    },
    {
        "slot": "emblem", "item_type": "equip",
        "name": "Gold Maple Leaf Emblem", "starforce": 0,
        "potential": {
            "option1": {"label": "ATT +12%"},
            "option2": {"label": "ATT +9%"},
            "option3": {"label": "ATT +9%"},
        },
        "bonus_potential": {},
    },
    {
        "slot": "hat", "item_type": "equip",
        "name": "Arcane Umbra Hat", "starforce": 20,
        "potential": {}, "bonus_potential": {},
    },
    {
        "slot": "secondary", "item_type": "equip",
        "name": "Arcane Umbra Quiver", "starforce": 18,
        "potential": {"option1": {"label": "ATT +9%"}},
        "bonus_potential": {},
    },
]

result = CombatPowerEngine.analyze_all_equipment(
    ap_stats, items, "Bowmaster", real_cp=5_000_000
)

result_data["bowmaster_5m"] = {
    "total_items_analyzed": len(result['items']),
    "char_cp_real": result['real_cp'],
    "char_cp_calc": result['calculated_cp'],
    "error_pct": round(abs(result['calculated_cp'] - 5_000_000) / 5_000_000 * 100, 2),
    "items": [
        {
            "name": it.get("name") or it.get("slot") or "?",
            "cp_contribution": it.get("cp_contribution", 0),
            "cp_pct": it.get("cp_contribution_pct", 0)
        }
        for it in result["items"]
    ],
}

# ─── Summary ────────────────────────────────────────────────────────────────
print("\n=== CP Engine Verification ===\n")
wa = result_data["wind_archer_lv80"]
print(f"Wind Archer Lv80:  real={wa['real_cp']}, calc={wa['calc_cp']}, error={wa['error_pct']}%")
bm = result_data["bowmaster_5m"]
print(f"Bowmaster 5M:      real={bm['char_cp_real']}, calc={bm['char_cp_calc']}, error={bm['error_pct']}%")
print()

with open("test_cp_out.json", "w", encoding="utf-8") as f:
    json.dump(result_data, f, indent=2)

print("Results saved to test_cp_out.json")
