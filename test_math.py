import sys
sys.path.append("C:\\Scripts\\Maple\\MapleGuard\\backend")
from services.calculator_engine import calculator_engine

print("--- Testing CP Estimation ---")
old_s = { "main_stat": 1000, "sub_stat": 500, "attack": 500, "attack_percent": 10, "damage_percent": 20, "boss_damage_percent": 10, "final_damage_percent": 0, "crit_damage_percent": 30 }
new_s = { "main_stat": 1050, "sub_stat": 520, "attack": 550, "attack_percent": 15, "damage_percent": 20, "boss_damage_percent": 10, "final_damage_percent": 0, "crit_damage_percent": 30 }
cp = calculator_engine.estimate_cp_gain(old_s, new_s, 4690140)
print(f"New CP: {cp}")

print("--- Testing Starforce EV ---")
sf_cost = calculator_engine.calc_starforce_ev(10, 15, 5000000, 0)
print(f"SF 10->15 Cost: {sf_cost:,.0f} NESO")

print("--- Testing Cube EV ---")
cube_cost = calculator_engine.calc_cube_ev("Epic", "Legendary", "Red", 15000000)
print(f"Red Cube Epic->Legendary: {cube_cost:,.0f} NESO")
