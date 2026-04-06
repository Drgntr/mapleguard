import json
from services.combat_power_engine import CombatPowerEngine, _calc_set_bonus_cp

result_data = {}

# Test set bonus calc
result_data["Arcane Umbra 8pc"] = _calc_set_bonus_cp('Arcane Umbra', 8, 5_000_000)
result_data["Arcane Umbra 7pc"] = _calc_set_bonus_cp('Arcane Umbra', 7, 5_000_000)
result_data["Genesis 8pc"] = _calc_set_bonus_cp('Genesis', 8, 12_000_000)

ap_stats = {
    "str": {"total": 18000, "base": 4, "enhance": 17996},
    "dex": {"total": 1500,  "base": 4, "enhance": 1496},
    "pad": {"total": 1200,  "base": 100, "enhance": 1100},
    "damage":             {"total": 60,  "base": 0, "enhance": 60},
    "bossMonsterDamage":  {"total": 230, "base": 0, "enhance": 230},
    "criticalDamage":     {"total": 50,  "base": 35,"enhance": 15},
    "attackPower": "5000000",
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

result_data["total_items_analyzed"] = len(result['items'])
result_data["char_cp_real"] = result['real_cp']
result_data["char_cp_calc"] = result['calculated_cp']
result_data["items"] = []

for it in result["items"]:
    result_data["items"].append({
        "name": it.get("name") or it.get("slot") or "?",
        "cp_contribution": it.get("cp_contribution", 0),
        "cp_pct": it.get("cp_contribution_pct", 0)
    })

with open("test_cp_out.json", "w", encoding="utf-8") as f:
    json.dump(result_data, f, indent=2)
