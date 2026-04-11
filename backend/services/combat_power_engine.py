"""
Combat Power (CP) Calculation Engine for MapleStory Universe (N).

Methodology:
  CP formula (adapted from KMS formula for MSU):

    CP = Stat × ATT × Damage × CDM

    Stat   = (4 × Primary + Secondary) / 100
    ATT    = Bow-standardized Attack Power (raw ATT for bow-equivalent weapons)
    Damage = 1 + (Damage% + BossDamage%) / 100
    CDM    = CP_CDM_BASE + equipCritDmg% / 100

  MSU uses CP_CDM_BASE = 0.70 (verified against real API data).
  KMS uses 1.35 as the hidden base crit constant, but MSU differs.

  NOT in CP: Final Damage%, Weapon Multiplier, IED%, skill/link bonuses.
  ATT is standardized to bow-equivalent; weapon multiplier is NOT used.

  IMPORTANT: The MSU API field `apStat.attackPower` is the REAL Combat Power
  (전투력), NOT the physical attack stat. Physical ATT is in `apStat.pad`.

  Per-item contributions use marginal (log-derivative) decomposition against
  the 4 multiplicative factors above, scaled to the real API CP value.

  An item's CP contribution % = Σ (item_factor_i / total_factor_i) for each factor.
  This is then applied to the real CP to get the absolute contribution.

Star Force Stat Gain Tables (MSU / MapleStory N):
  - Stat gains per star depend on item level bracket.
  - Stars 0-14: primary stat only (armor); stars 15+: primary + ATT bonus.
  - Values sourced from community reverse-engineering (KMS/GMS data, MapleStory wiki).
"""

from __future__ import annotations
import math
import re as _re
from typing import Dict, List, Optional, Tuple

# ─── MSU CP Formula Constants ─────────────────────────────────────────────────
# Base Critical Damage multiplier for CP calculation.
# MSU (MapleStory Universe / N) uses 0.70, verified against real API data
# (e.g. Wind Archer Lv80: DEX=528, STR=57, PAD=125, real CP=1897 → CDM=0.70).
# KMS uses 1.35 but MSU is a different game with a different formula constant.
CP_CDM_BASE: float = 0.70

# ─── Class → Primary / Secondary Stat Mapping ─────────────────────────────────
# Maps MSU job names to (primary_stat_key, secondary_stat_key)
# Primary stat gets 4× weight; secondary gets 1× in the stat component.
CLASS_STAT_MAP: Dict[str, Tuple[str, str]] = {
    # Warriors
    "Hero":              ("str", "dex"),
    "Paladin":           ("str", "dex"),
    "Dark Knight":       ("str", "dex"),
    # Mages
    "Fire/Poison":       ("int", "luk"),
    "Ice/Lightning":     ("int", "luk"),
    "Bishop":            ("int", "luk"),
    "Fire Poison":       ("int", "luk"),
    "Ice Lightning":     ("int", "luk"),
    # Archers
    "Bowmaster":         ("dex", "str"),
    "Marksman":          ("dex", "str"),
    "Pathfinder":        ("dex", "str"),
    # Thieves
    "Night Lord":        ("luk", "dex"),
    "Shadower":          ("luk", "dex"),
    "Dual Blade":        ("luk", "dex"),
    # Pirates
    "Buccaneer":         ("str", "dex"),
    "Corsair":           ("dex", "str"),
    "Cannoneer":         ("str", "dex"),
    # Cygnus Knights
    "Dawn Warrior":      ("str", "dex"),
    "Blaze Wizard":      ("int", "luk"),
    "Wind Archer":       ("dex", "str"),
    "Night Walker":      ("luk", "dex"),
    "Thunder Breaker":   ("str", "dex"),
    "Mihile":            ("str", "dex"),
    # Resistance
    "Demon Slayer":      ("str", "dex"),
    "Battle Mage":       ("int", "luk"),
    "Wild Hunter":       ("dex", "str"),
    "Mechanic":          ("dex", "str"),
    "Xenon":             ("all", "all"),   # special: uses all stats
    "Demon Avenger":     ("hp", "str"),    # special: HP-based
    "Blaster":           ("str", "dex"),
    # Heroes of Maple
    "Aran":              ("str", "dex"),
    "Evan":              ("int", "luk"),
    "Luminous":          ("int", "luk"),
    "Mercedes":          ("dex", "str"),
    "Phantom":           ("luk", "dex"),
    "Shade":             ("str", "dex"),
    # Nova
    "Kaiser":            ("str", "dex"),
    "Angelic Buster":    ("dex", "str"),
    "Cadena":            ("luk", "dex"),
    "Kain":              ("dex", "str"),
    # Flora
    "Adele":             ("str", "dex"),
    "Illium":            ("int", "luk"),
    "Ark":               ("str", "dex"),
    "Khali":             ("luk", "dex"),
    # Anima
    "Hoyoung":           ("luk", "dex"),
    "Lara":              ("int", "luk"),
    # Other
    "Hayato":            ("str", "dex"),
    "Kanna":             ("int", "luk"),
    "Zero":              ("str", "dex"),
    "Kinesis":           ("int", "luk"),
    "Lynn":              ("str", "dex"),
}

# ─── Class → Weapon Multiplier (for CP formula) ─────────────────────────────
# MapleStory CP formula uses the weapon multiplier directly:
#   CP = WeaponMult × (4P+S) × (ATT/100) × Dmg% × FD% × CD%
# Maps job name → default weapon multiplier.
CLASS_WEAPON_MULT: Dict[str, float] = {
    # Warriors (swords / 2H / spear / polearm)
    "Hero":              1.34,  # 2H Sword
    "Paladin":           1.34,  # 2H Sword (or 1H+Shield 1.20)
    "Dark Knight":       1.49,  # Spear/Polearm
    # Mages (wand / staff)
    "Fire/Poison":       1.20,
    "Ice/Lightning":     1.20,
    "Bishop":            1.20,
    "Fire Poison":       1.20,
    "Ice Lightning":     1.20,
    # Archers
    "Bowmaster":         1.30,  # Bow
    "Marksman":          1.35,  # Crossbow
    "Pathfinder":        1.30,  # Bow variant
    # Thieves
    "Night Lord":        1.75,  # Claw
    "Shadower":          1.30,  # Dagger
    "Dual Blade":        1.30,  # Dagger
    # Pirates
    "Buccaneer":         1.70,  # Knuckle
    "Corsair":           1.50,  # Gun
    "Cannoneer":         1.50,  # Hand Cannon
    # Cygnus Knights
    "Dawn Warrior":      1.34,
    "Blaze Wizard":      1.20,
    "Wind Archer":       1.30,
    "Night Walker":      1.75,
    "Thunder Breaker":   1.70,
    "Mihile":            1.20,  # 1H Sword + Shield
    # Resistance
    "Demon Slayer":      1.34,  # 2H Mace
    "Battle Mage":       1.20,  # Staff
    "Wild Hunter":       1.35,  # Crossbow
    "Mechanic":          1.50,  # Gun
    "Xenon":             1.30,  # Whip Blade
    "Demon Avenger":     1.30,  # Desperado
    "Blaster":           1.70,  # Arm Cannon
    # Heroes of Maple
    "Aran":              1.49,  # Polearm
    "Evan":              1.20,  # Staff
    "Luminous":          1.20,  # Shining Rod
    "Mercedes":          1.30,  # Dual Bowguns (bow mult)
    "Phantom":           1.30,  # Cane
    "Shade":             1.70,  # Knuckle
    # Nova
    "Kaiser":            1.34,  # 2H Sword
    "Angelic Buster":    1.30,  # Soul Shooter
    "Cadena":            1.30,  # Chain
    "Kain":              1.30,  # Whispershot
    # Flora
    "Adele":             1.34,  # Tuner/2H Sword
    "Illium":            1.20,  # Lucent Gauntlet
    "Ark":               1.70,  # Knuckle
    "Khali":             1.30,  # Chakram
    # Anima
    "Hoyoung":           1.30,  # Fan
    "Lara":              1.20,  # Scepter
    # Other
    "Hayato":            1.30,  # Katana
    "Kanna":             1.30,  # Fan
    "Zero":              1.34,  # 2H Sword
    "Kinesis":           1.20,  # Psy-limiter (Staff)
    "Lynn":              1.30,  # Glaive
}
DEFAULT_WEAPON_MULT: float = 1.30  # fallback

# ─── Weapon Multiplier Table (by weapon type, for damage range display) ──────
WEAPON_MULTIPLIER: Dict[str, float] = {
    "1H Sword":   1.20,
    "1H Axe":     1.20,
    "1H Blunt":   1.20,
    "2H Sword":   1.34,
    "2H Axe":     1.34,
    "2H Blunt":   1.34,
    "Spear":      1.49,
    "Polearm":    1.49,
    "Bow":        1.30,
    "Crossbow":   1.35,
    "Claw":       1.75,
    "Dagger":     1.30,
    "Cane":       1.30,
    "Gun":        1.50,
    "Knuckle":    1.70,
    "Wand":       1.20,
    "Staff":      1.20,
    "Fan":        1.30,
    "Two-Handed Sword": 1.34,
    "Desperado":  1.30,
    "Whip Blade": 1.30,
    "Arm Cannon":  1.70,
    "Chain":      1.30,
    "Ritual Fan": 1.30,
    "Tuner":      1.30,
    "Breath Shooter": 1.30,
    "Whispershot": 1.30,
    "Shining Rod": 1.20,
    "Lucent Gauntlet": 1.20,
    "Chakram":    1.30,
    "Katana":     1.30,
    "Scepter":    1.34,
}

# ─── Bow Base ATT by Equipment Tier ───────────────────────────────────────────
# Used for weapon standardization in CP calculation.
# Format: tier_name -> bow base ATT at that tier
BOW_BASE_ATT: Dict[str, int] = {
    "Fafnir":       197,
    "AbsoLab":      182,
    "Arcane Umbra":  276,
    "Genesis":      318,
    "Eternal":      318,  # same tier as Genesis in MSU N
}

# ─── Weapon Base ATT by Type and Tier ──────────────────────────────────────────
# Format: (weapon_type, tier) -> base ATT
# Only common weapon types included; expand as needed.
WEAPON_BASE_ATT: Dict[Tuple[str, str], int] = {
    # Fafnir tier
    ("Dagger", "Fafnir"):       184,
    ("Claw", "Fafnir"):         199,
    ("Bow", "Fafnir"):          197,
    ("Staff", "Fafnir"):        191,
    ("Wand", "Fafnir"):         189,
    ("1H Sword", "Fafnir"):     185,
    ("2H Sword", "Fafnir"):     190,
    ("Spear", "Fafnir"):        190,
    ("Polearm", "Fafnir"):      190,
    ("Gun", "Fafnir"):          195,
    ("Knuckle", "Fafnir"):      185,
    ("Crossbow", "Fafnir"):     197,
    # Arcane Umbra tier
    ("Dagger", "Arcane Umbra"):  258,
    ("Claw", "Arcane Umbra"):    284,
    ("Bow", "Arcane Umbra"):     276,
    ("Staff", "Arcane Umbra"):   270,
    ("Wand", "Arcane Umbra"):    267,
    ("1H Sword", "Arcane Umbra"):261,
    ("2H Sword", "Arcane Umbra"):269,
    ("Spear", "Arcane Umbra"):   269,
    ("Polearm", "Arcane Umbra"): 269,
    ("Gun", "Arcane Umbra"):     279,
    ("Knuckle", "Arcane Umbra"): 261,
    ("Crossbow", "Arcane Umbra"):276,
    # Genesis / Eternal tier
    ("Dagger", "Genesis"):       296,
    ("Claw", "Genesis"):         326,
    ("Bow", "Genesis"):          318,
    ("Staff", "Genesis"):        310,
    ("Wand", "Genesis"):         307,
    ("1H Sword", "Genesis"):     300,
    ("2H Sword", "Genesis"):     309,
    ("Spear", "Genesis"):        309,
    ("Polearm", "Genesis"):      309,
    ("Gun", "Genesis"):          321,
    ("Knuckle", "Genesis"):      300,
    ("Crossbow", "Genesis"):     318,
}

# ─── Comprehensive Starforce Stat Gain Tables ──────────────────────────────────
#
# Per-star stat gains for ARMOR items (hat, top, bottom, glove, shoe, cape, etc.)
# and WEAPON items. Values verified against KMS/GMS community data.
#
# Format: (item_level_min, item_level_max): [stat_gain_per_star_0..25]
#   - For armor: values represent PRIMARY STAT per star (on success)
#   - Stars 15+ also add ATT/M.ATT (see SF_WEAPON_ATT by bracket below)
#
# Source: Community reverse-engineering from MapleStory wiki + calculator tools
# Note: MapleStory N uses the same base formula as KMS. Superior items are excluded.
#
# The stat gain formula is: ceil(item_level^2 / 1000 + bonus) approximately,
# but is more precisely captured in these lookup tables from game data.
#
# ─────────────────────────────────────────────────────────────────────────────────

# Armor primary stat gained per star (armor type: hat, glove, shoes, etc.)
# Each tuple: (before_star → after_star) stat gain
# Indexed [star_from_0_to_22] for each level bracket
SF_ARMOR_STAT: Dict[Tuple[int, int], List[int]] = {
    # Lv 130-139
    (130, 139): [2,2,2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,3,3,3,3,3,3,4,4],
    # Lv 140-149
    (140, 149): [2,2,2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,3,3,3,3,3,4,4,4],
    # Lv 150-159
    (150, 159): [2,2,2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,4,4,4,4,4,4,5,5],
    # Lv 160-179
    (160, 179): [3,3,3,3,3,3,3,3,3,3,4,4,4,4,4,4,4,5,5,5,5,5,5,6,6],
    # Lv 180-199
    (180, 199): [4,4,4,4,4,4,4,4,4,4,5,5,5,5,5,6,6,7,7,7,7,7,8,9,9],
    # Lv 200-219  (Arcane Umbra tier)
    (200, 219): [5,5,5,5,5,5,5,5,5,5,6,6,6,6,6,7,7,9,9,9,9,9,10,11,12],
    # Lv 220-239
    (220, 239): [5,5,5,5,5,6,6,6,6,6,7,7,7,7,7,8,8,10,10,10,11,11,12,13,14],
    # Lv 240+    (Genesis / Eternal tier)
    (240, 299): [6,6,6,6,6,7,7,7,7,7,8,8,8,8,8,10,10,12,12,12,13,13,14,15,16],
}

# Weapon ATT gained from starforce (per star on success) — for weapons only
# These are the INCREMENTAL attack bonuses each star level adds
# Format: {item_level_bracket: [att_gain_at_star_0..24]}
# Stars 0-12 give 0 ATT bonus. Stars 13+ give ATT.
SF_WEAPON_ATT: Dict[Tuple[int, int], List[int]] = {
    (130, 139): [0]*13 + [1,1,2,2,3,3,3,3,4,5,5,6,7],
    (140, 149): [0]*13 + [1,2,2,2,3,3,3,4,4,5,6,7,8],
    (150, 159): [0]*13 + [2,2,2,3,3,4,4,4,5,6,7,8,9],
    (160, 179): [0]*13 + [2,2,3,3,4,4,5,5,6,7,8,9,10],
    (180, 199): [0]*13 + [3,3,4,4,5,6,6,7,8,9,10,12,14],
    (200, 219): [0]*13 + [4,4,5,5,7,7,8,8,10,12,14,16,18],
    (220, 239): [0]*13 + [5,5,6,6,8,8,9,9,11,13,15,18,20],
    (240, 299): [0]*13 + [6,6,7,7,9,9,11,11,13,15,18,21,24],
}

# ATT bonus added to ARMOR items at stars 15+ (much smaller than weapon bonus)
# Indexed by star [0..24]
SF_ARMOR_ATT_BONUS: Dict[Tuple[int, int], List[int]] = {
    (130, 139): [0]*15 + [0,0,1,1,1,1,1,1,2,2],
    (140, 149): [0]*15 + [0,0,1,1,1,1,1,2,2,2],
    (150, 159): [0]*15 + [0,1,1,1,2,2,2,2,2,3],
    (160, 179): [0]*15 + [1,1,1,2,2,2,2,3,3,3],
    (180, 199): [0]*15 + [1,1,2,2,3,3,3,4,4,5],
    (200, 219): [0]*15 + [2,2,3,3,4,4,5,5,6,7],
    (220, 239): [0]*15 + [2,2,3,4,4,5,6,6,7,8],
    (240, 299): [0]*15 + [3,3,4,5,5,6,7,7,8,9],
}

# Cumulative stat gains from 0 to N stars (for level bracket lookup)
# These are cached versions — computed on first use.
_SF_ARMOR_STAT_CUMUL: Dict[Tuple[int, int], List[int]] = {}
_SF_WEAPON_ATT_CUMUL: Dict[Tuple[int, int], List[int]] = {}
_SF_ARMOR_ATT_CUMUL: Dict[Tuple[int, int], List[int]] = {}


def _estimate_total_stat_pct(real_cp: int) -> float:
    """
    Estimate the character's total %STAT from all sources based on CP bracket.

    The API's apStat gives total stat values with %STAT already applied.
    To convert an item's %STAT line to a flat equivalent, we need to know the
    "base stat" (stat without %bonuses).  Since the API doesn't provide %STAT
    directly, we estimate it from the character's CP level.

    Returns estimated total %STAT (e.g. 150 means +150% from gear/buffs).
    """
    if real_cp >= 5_000_000:
        return 250.0   # Endgame: full legendary %STAT on multiple pieces
    if real_cp >= 1_000_000:
        return 180.0   # Late game: mix of legendary/unique potentials
    if real_cp >= 100_000:
        return 100.0   # Mid game: some epic/unique %STAT potentials
    if real_cp >= 10_000:
        return 40.0    # Early-mid: few %STAT sources
    return 0.0         # Early game: no %STAT potentials


def _estimate_total_att_pct(real_cp: int) -> float:
    """
    Estimate the character's total %ATT from all sources based on CP bracket.

    The API's pad.total already includes %ATT from equipment potentials.
    To convert an item's %ATT potential to a flat ATT equivalent, we need
    "base ATT" (ATT without %ATT).  We estimate total %ATT from CP bracket.

    Returns estimated total %ATT (e.g. 120 means +120% from potentials).
    """
    if real_cp >= 5_000_000:
        return 200.0   # Endgame: 3 legendary ATT% sources + familiars/etc
    if real_cp >= 1_000_000:
        return 130.0   # Late game: weapon + emblem legendary, secondary unique
    if real_cp >= 100_000:
        return 60.0    # Mid game: some ATT% potentials
    if real_cp >= 10_000:
        return 20.0    # Early-mid: minimal ATT%
    return 0.0         # Early game: no ATT% potentials


def _get_level_bracket(item_level: int) -> Optional[Tuple[int, int]]:
    """Find the item level bracket for starforce tables."""
    for bracket in SF_ARMOR_STAT.keys():
        if bracket[0] <= item_level <= bracket[1]:
            return bracket
    # Clamp to highest bracket for items above 299
    if item_level > 240:
        return (240, 299)
    # Clamp to lowest bracket for items below 130
    if item_level < 130:
        return (130, 139)
    return None


def get_sf_stat_gain(item_level: int, from_star: int, to_star: int, is_weapon: bool = False) -> Dict[str, int]:
    """
    Calculate the primary stat and ATT gained from starforcing an item
    from `from_star` to `to_star` stars.

    Returns:
        {
          "primary_stat": total primary stat gain,
          "att": total attack/magic attack gain,
          "cumulative_att": total ATT at to_star level (from 0),
          "cumulative_stat": total stat at to_star level (from 0)
        }
    """
    bracket = _get_level_bracket(item_level)
    if bracket is None:
        return {"primary_stat": 0, "att": 0, "cumulative_att": 0, "cumulative_stat": 0}

    armor_stats = SF_ARMOR_STAT.get(bracket, [])
    weapon_att = SF_WEAPON_ATT.get(bracket, []) if is_weapon else []
    armor_att = SF_ARMOR_ATT_BONUS.get(bracket, []) if not is_weapon else []

    from_star = max(0, min(from_star, 24))
    to_star = max(0, min(to_star, 25))
    if to_star <= from_star:
        return {"primary_stat": 0, "att": 0, "cumulative_att": 0, "cumulative_stat": 0}

    # Sum incremental gains from from_star to to_star-1
    total_stat = 0
    total_att = 0
    for star in range(from_star, min(to_star, len(armor_stats))):
        if star < len(armor_stats):
            total_stat += armor_stats[star]
        att_table = weapon_att if is_weapon else armor_att
        if star < len(att_table):
            total_att += att_table[star]

    # Also compute cumulative from star 0 to to_star (for full item value context)
    cum_stat = sum(armor_stats[:min(to_star, len(armor_stats))])
    cum_att = 0
    att_table = weapon_att if is_weapon else armor_att
    cum_att = sum(att_table[:min(to_star, len(att_table))])

    return {
        "primary_stat": total_stat,
        "att": total_att,
        "cumulative_stat": cum_stat,
        "cumulative_att": cum_att,
    }


# Legacy compatibility alias (kept for existing code)
SF_WEAPON_ATT_BONUS: Dict[int, int] = {
    0: 0,  1: 0,  2: 0,  3: 0,  4: 0,  5: 0,
    6: 0,  7: 0,  8: 0,  9: 0,  10: 0,
    11: 0,  12: 0,  13: 7,  14: 7,  15: 8,
    16: 9,  17: 10,  18: 11,  19: 12,  20: 13,
    21: 15,  22: 17,  23: 20,  24: 24,  25: 29,
}


class CombatPowerEngine:
    """
    Calculates Combat Power using the real MapleStory formula with
    percentage-scaling methodology for accuracy.

    Flow:
    1. Build stat profile from character data (AP stats + equipment)
    2. Calculate "Calculated CP" using the formula
    3. Use ratio against real MSU CP for percentage-based scaling
    4. For upgrades: calculate delta between old/new Calculated CP
    """

    # ── Core CP Formula ──────────────────────────────────────────────────────

    @staticmethod
    def calc_stat_component(
        primary: float,
        secondary: float,
    ) -> float:
        """Stat = (4 × Primary + Secondary)"""
        return 4.0 * primary + secondary

    @staticmethod
    def calc_standardized_att(
        total_att: float,
        att_percent: float,
        weapon_base_att: int = 0,
        bow_base_att: int = 0,
        weapon_sf_att: int = 0,
    ) -> float:
        """
        Standardized ATT converts weapon ATT to bow-equivalent for CP.

        StdATT = (ATT + floor((bowBase/weaponBase - 1) × (weaponBase + weaponSF_ATT))) × (1 + %ATT/100)

        If weapon base ATTs are unknown, falls back to raw ATT × (1 + %ATT/100).
        """
        att = total_att
        if weapon_base_att > 0 and bow_base_att > 0 and weapon_base_att != bow_base_att:
            bow_ratio = bow_base_att / weapon_base_att
            bonus = math.floor((bow_ratio - 1) * (weapon_base_att + weapon_sf_att))
            att = total_att + bonus

        return att * (1.0 + att_percent / 100.0)

    @staticmethod
    def calc_damage_mult(damage_pct: float, boss_damage_pct: float = 0) -> float:
        """Damage multiplier for CP: 1 + (Damage% + BossDmg%) / 100.

        Both general Damage% and Boss Damage% are included in CP (전투력).
        Source: NamuWiki / StrategyWiki / OrangeMushroom KMST 1.2.162.
        """
        return 1.0 + (damage_pct + boss_damage_pct) / 100.0

    @staticmethod
    def calc_final_damage_mult(final_damage_pct: float) -> float:
        """Final Damage multiplier: 1 + FD% / 100.
        NOTE: FD is NOT part of the CP formula. This helper is kept for
        damage range calculations and other non-CP uses."""
        return 1.0 + final_damage_pct / 100.0

    @staticmethod
    def calc_crit_damage_mult(crit_damage_pct: float, crit_damage_base: float = 0) -> float:
        """Critical Damage multiplier for CP: CP_CDM_BASE + equipCD% / 100.

        MSU uses CP_CDM_BASE = 0.70 (verified against real API data).
        KMS uses 1.35 but MSU is a different game.

        API behavior:
          - If criticalDamage.base >= 30 → total already includes the base,
            so equipCD = total - base.
          - If criticalDamage.base < 30  → total is equipment-only,
            so equipCD = total.
        Either way: CDM = CP_CDM_BASE + equipCD / 100.
        """
        if crit_damage_base >= 30:
            equip_cd = crit_damage_pct - crit_damage_base
        else:
            equip_cd = crit_damage_pct
        return CP_CDM_BASE + equip_cd / 100.0

    @classmethod
    def calculate_cp(
        cls,
        primary_stat: float,
        secondary_stat: float,
        total_att: float,
        att_percent: float = 0.0,
        damage_pct: float = 0.0,
        boss_damage_pct: float = 0.0,
        final_damage_pct: float = 0.0,
        crit_damage_pct: float = 0.0,
        crit_damage_base: float = 0.0,
        weapon_base_att: int = 0,
        bow_base_att: int = 0,
        weapon_sf_att: int = 0,
        **kwargs,
    ) -> float:
        """
        MSU Combat Power (전투력) calculation.

        CP = Stat × StdATT × Damage × CDM

        Where:
          Stat   = (4 × Primary + Secondary) / 100
          StdATT = Bow-standardized ATT (for bow-equivalent weapons, = raw ATT)
          Damage = 1 + (Damage% + BossDmg%) / 100
          CDM    = CP_CDM_BASE + equipCD% / 100  (MSU: 0.70)

        NOT included: Final Damage%, Weapon Multiplier, IED%.
        ATT is standardized to bow-equivalent (no weapon mult needed).
        """
        stat = cls.calc_stat_component(primary_stat, secondary_stat)

        # Use Magic Attack if provided and higher than Physical (for Mages)
        actual_att = max(total_att, kwargs.get("total_matt", 0))

        std_att = cls.calc_standardized_att(
            actual_att, att_percent, weapon_base_att, bow_base_att, weapon_sf_att
        )
        dmg = cls.calc_damage_mult(damage_pct, boss_damage_pct)
        cd = cls.calc_crit_damage_mult(crit_damage_pct, crit_damage_base)

        # CP formula: Stat/100 × ATT × Damage × CDM
        # Since stat = (4P+S) and std_att already has /100 applied via
        # calc_standardized_att returning raw value, we divide by 100 here.
        result = (stat / 100.0) * std_att * dmg * cd

        # Ensure a meaningful minimum if we have any stats at all
        if result <= 0 and (primary_stat > 0 or actual_att > 0):
             result = (stat * 2.0) + (actual_att * 5.0) + 1000.0

        return result

    # ── Stats Extraction from Character Data ──────────────────────────────────

    @staticmethod
    def detect_primary_secondary(
        job_name: str,
        ap_stats: Optional[dict] = None,
    ) -> Tuple[str, str]:
        """
        Determine primary and secondary stat keys for a given job.
        Falls back to auto-detection from highest stat if job not mapped.
        """
        if job_name in CLASS_STAT_MAP:
            return CLASS_STAT_MAP[job_name]

        # Try partial match
        for name, stats in CLASS_STAT_MAP.items():
            if name.lower() in job_name.lower() or job_name.lower() in name.lower():
                return stats

        # Auto-detect from highest stat
        if ap_stats:
            stat_totals = {
                "str": _get_stat_total(ap_stats, "str_stat", "str"),
                "dex": _get_stat_total(ap_stats, "dex"),
                "int": _get_stat_total(ap_stats, "int_stat", "int"),
                "luk": _get_stat_total(ap_stats, "luk"),
            }
            sorted_stats = sorted(stat_totals.items(), key=lambda x: x[1], reverse=True)
            primary_key = sorted_stats[0][0]
            # Typical secondary is the second-highest non-primary
            secondary_key = sorted_stats[1][0]
            return (primary_key, secondary_key)

        return ("str", "dex")  # default fallback

    @classmethod
    def extract_stats_from_character(
        cls,
        ap_stats: dict,
        job_name: str = "",
    ) -> Dict[str, float]:
        """
        Extract all CP-relevant stats from character's AP stats.
        Returns a flat dict with all stat values.
        """
        if not ap_stats:
            ap_stats = {}
        primary_key, secondary_key = cls.detect_primary_secondary(job_name, ap_stats)

        # Map stat keys to AP stat field names
        stat_key_map = {
            "str": ["str_stat", "str"],
            "dex": ["dex"],
            "int": ["int_stat", "int"],
            "luk": ["luk"],
            "hp": ["hp"],
        }

        primary_val = 0.0
        secondary_val = 0.0

        if primary_key == "all":
            # Xenon: uses all stats
            primary_val = sum(
                _get_stat_total(ap_stats, *stat_key_map.get(k, [k]))
                for k in ["str", "dex", "luk"]
            ) / 3.0
            secondary_val = primary_val
        else:
            primary_val = _get_stat_total(ap_stats, *stat_key_map.get(primary_key, [primary_key]))
            secondary_val = _get_stat_total(ap_stats, *stat_key_map.get(secondary_key, [secondary_key]))

        return {
            "primary_stat": primary_val,
            "secondary_stat": secondary_val,
            "primary_key": primary_key,
            "secondary_key": secondary_key,
            "total_att": _get_stat_total(ap_stats, "attack", "pad", "mad", "physicalAttack", "magicalAttack", "attackAndMagicAttack"),
            "att_percent": 0.0,  # %ATT is embedded in the total; we account via equipment aggregation
            "damage_pct": _get_stat_total(ap_stats, "damage", "damageRate"),
            "boss_damage_pct": _get_stat_total(ap_stats, "boss_monster_damage", "bossMonsterDamage", "bossDamage"),
            "final_damage_pct": _get_stat_total(ap_stats, "final_damage", "finalDamage"),
            "crit_damage_pct": _get_stat_total(ap_stats, "critical_damage", "criticalDamage", "critDamage"),
        }

    # ── Per-Item CP Contribution ─────────────────────────────────────────────

    @classmethod
    def calculate_item_cp_value(
        cls,
        character_stats: Dict[str, float],
        item_stats: Dict[str, float],
        real_cp: int = 0,
    ) -> Dict[str, any]:
        """
        Calculate how much CP a single item contributes to the character.

        Method: Marginal (log-derivative) decomposition.

        MSU's CP formula is approximately:
            CP ≈ (4×Primary + Secondary) × ATT × small_multipliers

        In log-space, each multiplicative factor contributes additively:
            ln(CP) = ln(StatComponent) + ln(ATT) + ...

        An item's percentage contribution is the sum of its fractional
        contributions to each factor:
            item_pct ≈ (4×item_P + item_S) / (4×P + S)
                      + item_ATT / total_ATT
                      + item_ATT% / (100 + total_ATT%)
                      + ...

        This avoids the cascading over-estimation of the old delta (removal) method,
        where removing one item's stats from a multiplicative formula produced
        disproportionately large deltas.

        Args:
            character_stats: Full character stats (from extract_stats_from_character)
            item_stats: The item's stat contributions (from extract_item_stats)
            real_cp: The character's real CP from MSU API (for scaling)

        Returns dict with:
            - cp_contribution: absolute CP the item adds (scaled to real CP)
            - cp_contribution_pct: percentage of total CP
            - real_cp_contribution: same as cp_contribution (kept for compatibility)
            - stat_breakdown: per-stat contribution analysis
        """
        breakdown = cls._calc_stat_breakdown_marginal(character_stats, item_stats, real_cp)

        total_pct = sum(entry["cp_pct"] for entry in breakdown)
        base_cp = real_cp if real_cp > 0 else cls.calculate_cp(
            primary_stat=character_stats["primary_stat"],
            secondary_stat=character_stats["secondary_stat"],
            total_att=character_stats.get("total_att", 0),
            att_percent=character_stats.get("att_percent", 0),
            damage_pct=character_stats.get("damage_pct", 0),
            boss_damage_pct=character_stats.get("boss_damage_pct", 0),
            final_damage_pct=character_stats.get("final_damage_pct", 0),
            crit_damage_pct=character_stats.get("crit_damage_pct", 0),
        )
        contribution = int(base_cp * total_pct / 100.0)

        return {
            "cp_contribution": contribution,
            "cp_contribution_pct": round(total_pct, 2),
            "real_cp_contribution": contribution,
            "stat_breakdown": breakdown,
        }

    @classmethod
    def _calc_stat_breakdown_marginal(
        cls,
        char_stats: Dict[str, float],
        item_stats: Dict[str, float],
        real_cp: int = 0,
    ) -> List[Dict[str, any]]:
        """
        Break down an item's CP contribution using marginal percentages.

        The API's apStat returns TOTAL values (e.g. pad.total = 1200) which
        already include all %ATT/%STAT bonuses baked in.  Therefore we CANNOT
        treat %ATT as a separate multiplicative factor — it is already inside
        the ATT total.  Instead, we convert %ATT and %STAT contributions to
        flat equivalents and merge them into their respective factors.

        Factors used (4 multiplicative CP components):
            1. Stat Component  = (4 × Primary + Secondary) / 100  — includes %STAT
            2. ATT             = total_att (pad.total)             — includes %ATT
            3. Damage%         = 1 + (DMG% + BossDMG%) / 100
            4. Crit Damage%    = CP_CDM_BASE + equipCD% / 100  (MSU: 0.70)
        NOT in CP: Final Damage%, Weapon Multiplier, IED%.
        """
        breakdown = []

        # ── Estimate total %STAT and %ATT for base value calculation ──
        # The character's total stat already includes %STAT from equipment.
        # We need to estimate "base stat" (without %STAT) to convert an
        # item's %STAT line to a flat stat equivalent.
        #
        # Heuristic: estimate total %STAT based on real CP bracket.
        est_total_stat_pct = _estimate_total_stat_pct(real_cp)
        est_total_att_pct = _estimate_total_att_pct(real_cp)

        char_primary = char_stats.get("primary_stat", 0)
        char_secondary = char_stats.get("secondary_stat", 0)

        # Estimate "base" values (before %bonuses were applied)
        base_primary = char_primary / (1.0 + est_total_stat_pct / 100.0) if est_total_stat_pct > 0 else char_primary
        base_secondary = char_secondary / (1.0 + est_total_stat_pct / 100.0) if est_total_stat_pct > 0 else char_secondary

        total_att = char_stats.get("total_att", 0)
        base_att = total_att / (1.0 + est_total_att_pct / 100.0) if est_total_att_pct > 0 else total_att

        # ── Factor 1: Stat Component = (4 × Primary + Secondary) ──
        # Merge %STAT into flat by converting: item_%STAT → base_stat × %STAT / 100
        stat_comp = 4.0 * char_primary + char_secondary
        if stat_comp > 0:
            item_flat = 4.0 * item_stats.get("primary_stat", 0) + item_stats.get("secondary_stat", 0)

            pct_primary = item_stats.get("primary_pct", 0)
            pct_secondary = item_stats.get("secondary_pct", 0)
            item_from_pct = (
                4.0 * base_primary * pct_primary / 100.0
                + base_secondary * pct_secondary / 100.0
            )

            total_item_stat = item_flat + item_from_pct
            pct = total_item_stat / stat_comp * 100.0

            if pct > 0:
                breakdown.append({
                    "stat": "Main Stat + Sub Stat",
                    "stat_key": "stat_component",
                    "item_value": round(total_item_stat, 1),
                    "cp_contribution": int(real_cp * pct / 100.0) if real_cp else 0,
                    "cp_pct": round(pct, 2),
                })

        # ── Factor 2: Attack Power (merged with %ATT) ──
        # Convert item %ATT → base_att × %ATT / 100, add to flat ATT contribution.
        if total_att > 0:
            item_flat_att = item_stats.get("total_att", 0)
            item_att_pct = item_stats.get("att_percent", 0)
            item_att_from_pct = base_att * item_att_pct / 100.0

            total_item_att = item_flat_att + item_att_from_pct
            if total_item_att > 0:
                pct = total_item_att / total_att * 100.0
                breakdown.append({
                    "stat": "Attack Power",
                    "stat_key": "total_att",
                    "item_value": round(total_item_att, 1),
                    "cp_contribution": int(real_cp * pct / 100.0) if real_cp else 0,
                    "cp_pct": round(pct, 2),
                })

        # ── Factor 3: Damage % + Boss Damage % ──
        char_dmg = char_stats.get("damage_pct", 0)
        char_boss = char_stats.get("boss_damage_pct", 0)
        dmg_total = 100.0 + char_dmg + char_boss
        item_dmg = item_stats.get("damage_pct", 0) + item_stats.get("boss_damage_pct", 0)
        if dmg_total > 100.0 and item_dmg > 0:
            pct = item_dmg / dmg_total * 100.0
            breakdown.append({
                "stat": "Damage % + Boss %",
                "stat_key": "damage_pct",
                "item_value": round(item_dmg, 1),
                "cp_contribution": int(real_cp * pct / 100.0) if real_cp else 0,
                "cp_pct": round(pct, 2),
            })

        # ── Factor 4: Critical Damage % ──
        # CDM = CP_CDM_BASE + equipCD/100. Denominator for marginal = CP_CDM_BASE*100 + equipCD.
        char_cd = char_stats.get("crit_damage_pct", 0)
        char_cd_base = char_stats.get("crit_damage_base", 0)
        equip_cd = char_cd - char_cd_base if char_cd_base >= 30 else char_cd
        cd_denom = CP_CDM_BASE * 100.0 + equip_cd  # from CDM = CP_CDM_BASE + equip_cd/100
        item_cd = item_stats.get("crit_damage_pct", 0)
        if cd_denom > 135.0 and item_cd > 0:
            pct = item_cd / cd_denom * 100.0
            breakdown.append({
                "stat": "Critical Damage %",
                "stat_key": "crit_damage_pct",
                "item_value": round(item_cd, 1),
                "cp_contribution": int(real_cp * pct / 100.0) if real_cp else 0,
                "cp_pct": round(pct, 2),
            })

        breakdown.sort(key=lambda x: x["cp_pct"], reverse=True)
        return breakdown

    # ── Upgrade Simulation ───────────────────────────────────────────────────

    @classmethod
    def estimate_upgrade_cp(
        cls,
        old_stats: Dict[str, float],
        new_stats: Dict[str, float],
        real_cp: int,
    ) -> Dict[str, any]:
        """
        Estimate CP change from stat changes (e.g., starforce upgrade, potential change).

        Uses marginal (log-derivative) decomposition consistent with the per-item
        calculation.  For each stat factor, the percentage gain is:
            dFi / Fi  (where dFi = new_value - old_value)
        Total CP gain% ≈ sum of all factor gain%.

        Args:
            old_stats: Current stat profile
            new_stats: Projected stat profile after upgrade
            real_cp: Character's real CP from MSU API

        Returns dict with CP projections and margin of error.
        """
        def _v(d, *keys):
            for k in keys:
                v = d.get(k)
                if v is not None and v != 0:
                    return float(v)
            return 0.0

        # Extract values with multiple key fallbacks (old/new may use different naming)
        old_primary = _v(old_stats, "primary_stat", "main_stat")
        new_primary = _v(new_stats, "primary_stat", "main_stat")
        old_secondary = _v(old_stats, "secondary_stat", "sub_stat")
        new_secondary = _v(new_stats, "secondary_stat", "sub_stat")
        old_att = _v(old_stats, "total_att", "attack")
        new_att = _v(new_stats, "total_att", "attack")
        old_attp = _v(old_stats, "att_percent", "attack_percent")
        new_attp = _v(new_stats, "att_percent", "attack_percent")
        # Damage% + Boss Damage% (both in CP)
        old_dmg = _v(old_stats, "damage_pct", "damage_percent") + _v(old_stats, "boss_damage_pct", "boss_damage_percent")
        new_dmg = _v(new_stats, "damage_pct", "damage_percent") + _v(new_stats, "boss_damage_pct", "boss_damage_percent")
        old_cd = _v(old_stats, "crit_damage_pct", "crit_damage_percent")
        new_cd = _v(new_stats, "crit_damage_pct", "crit_damage_percent")

        # Marginal % gain from each of the 4 CP factors
        pct_change = 0.0

        # Factor 1: Stat component (4P + S) / 100
        old_stat_comp = 4.0 * old_primary + old_secondary
        new_stat_comp = 4.0 * new_primary + new_secondary
        if old_stat_comp > 0:
            pct_change += (new_stat_comp - old_stat_comp) / old_stat_comp

        # Factor 2: Attack (bow-standardized)
        if old_att > 0 and new_att != old_att:
            pct_change += (new_att - old_att) / old_att

        # Attack % (merged into ATT factor)
        old_att_factor = 100.0 + old_attp
        new_att_factor = 100.0 + new_attp
        if old_att_factor > 0 and new_attp != old_attp:
            pct_change += (new_att_factor - old_att_factor) / old_att_factor

        # Factor 3: Damage% + Boss% = 1 + (dmg+boss)/100
        old_dmg_factor = 100.0 + old_dmg
        new_dmg_factor = 100.0 + new_dmg
        if old_dmg_factor > 0 and new_dmg != old_dmg:
            pct_change += (new_dmg_factor - old_dmg_factor) / old_dmg_factor

        # Factor 4: CDM = CP_CDM_BASE + cd/100 → denominator = CP_CDM_BASE*100 + cd
        old_cd_factor = CP_CDM_BASE * 100.0 + old_cd
        new_cd_factor = CP_CDM_BASE * 100.0 + new_cd
        if old_cd_factor > 0 and new_cd != old_cd:
            pct_change += (new_cd_factor - old_cd_factor) / old_cd_factor

        estimated_new_cp = int(real_cp * (1.0 + pct_change))
        cp_gain = estimated_new_cp - real_cp

        # Margin of error: ±15% on the GAIN (not total CP)
        margin = abs(cp_gain) * 0.15
        margin_low = estimated_new_cp - int(margin)
        margin_high = estimated_new_cp + int(margin)

        return {
            "estimated_new_cp": estimated_new_cp,
            "cp_gain": cp_gain,
            "cp_gain_pct": round(pct_change * 100, 2),
            "margin_low": margin_low,
            "margin_high": margin_high,
        }

    # ── Starforce-Specific CP Upgrade Calculation ────────────────────────────

    @classmethod
    def calculate_sf_cp_delta(
        cls,
        char_stats: Dict[str, float],
        real_cp: int,
        item_level: int,
        from_star: int,
        to_star: int,
        is_weapon: bool = False,
        item_type: str = "armor",
    ) -> Dict[str, any]:
        """
        Calculate the precise CP gained by starforcing an item from `from_star`
        to `to_star`. Uses the comprehensive starforce stat tables.

        This is what the "Combat Rating Upgrade" display shows — the estimated
        real CP number added to the character by this specific upgrade.

        Args:
            char_stats: Full character stat profile (from extract_stats_from_character)
            real_cp: Character's real CP from MSU API
            item_level: Item's required level (used to look up stat table)
            from_star: Current star count
            to_star: Target star count
            is_weapon: True if item is a weapon (gets ATT from earlier stars)
            item_type: "weapon" | "armor" | "accessory"

        Returns:
            {
                "cp_gain": estimated CP gained (real scale),
                "cp_gain_pct": percentage increase,
                "stat_delta": {"primary_stat": N, "att": N},
                "per_star": [{star, stat_gain, att_gain, cumulative_stat, cumulative_att}],
                "estimated_new_cp": new total CP estimate,
                "margin_low": low estimate,
                "margin_high": high estimate
            }
        """
        is_weapon_item = is_weapon or item_type.lower() == "weapon"

        # Get stat gains from the SF tables
        sf_gains = get_sf_stat_gain(item_level, from_star, to_star, is_weapon=is_weapon_item)
        primary_stat_delta = sf_gains["primary_stat"]
        att_delta = sf_gains["att"]

        # Build new stat profile with sf gains added
        new_stats = {k: v for k, v in char_stats.items()}
        new_stats["primary_stat"] = char_stats.get("primary_stat", 0) + primary_stat_delta
        new_stats["total_att"] = char_stats.get("total_att", 0) + att_delta

        # Calculate CP delta
        result = cls.estimate_upgrade_cp(char_stats, new_stats, real_cp)

        # Per-star breakdown
        per_star_data = []
        bracket = _get_level_bracket(item_level)
        if bracket:
            armor_tbl = SF_ARMOR_STAT.get(bracket, [])
            att_tbl = (SF_WEAPON_ATT if is_weapon_item else SF_ARMOR_ATT_BONUS).get(bracket, [])
            cum_stat = sum(armor_tbl[:from_star]) if from_star < len(armor_tbl) else sum(armor_tbl)
            cum_att = sum(att_tbl[:from_star]) if from_star < len(att_tbl) else sum(att_tbl)

            for star in range(from_star, min(to_star, 25)):
                s_gain = armor_tbl[star] if star < len(armor_tbl) else 0
                a_gain = att_tbl[star] if star < len(att_tbl) else 0
                cum_stat += s_gain
                cum_att += a_gain

                # Estimate cp at this star level
                mid_stats = {k: v for k, v in char_stats.items()}
                mid_stats["primary_stat"] = char_stats.get("primary_stat", 0) + (cum_stat - sum(armor_tbl[:from_star]))
                mid_stats["total_att"] = char_stats.get("total_att", 0) + (cum_att - (sum(att_tbl[:from_star]) if from_star < len(att_tbl) else sum(att_tbl)))
                mid_result = cls.estimate_upgrade_cp(char_stats, mid_stats, real_cp)

                per_star_data.append({
                    "star": star + 1,  # star we're going to
                    "stat_gain": s_gain,
                    "att_gain": a_gain,
                    "cumulative_stat_from_0": cum_stat,
                    "cumulative_att_from_0": cum_att,
                    "cp_at_this_star": mid_result.get("estimated_new_cp", real_cp),
                    "cp_gain_from_current": mid_result.get("cp_gain", 0),
                })

        return {
            "cp_gain": result.get("cp_gain", 0),
            "cp_gain_pct": result.get("cp_gain_pct", 0),
            "estimated_new_cp": result.get("estimated_new_cp", real_cp),
            "margin_low": result.get("margin_low", real_cp),
            "margin_high": result.get("margin_high", real_cp),
            "stat_delta": {
                "primary_stat": primary_stat_delta,
                "att": att_delta,
            },
            "per_star": per_star_data,
        }

    @classmethod
    def estimate_potential_cp_delta(
        cls,
        char_stats: Dict[str, float],
        real_cp: int,
        potential_lines: Dict[str, float],
    ) -> Dict[str, any]:
        """
        Estimate CP gain from potential lines being re-rolled to specific values.

        potential_lines dict example:
            {"primary_stat": 15, "boss_damage_pct": 30, "att": 10}

        Returns same structure as calculate_sf_cp_delta.
        """
        new_stats = {k: v for k, v in char_stats.items()}

        # Map potential line keys to char_stats keys
        key_map = {
            "primary_stat": "primary_stat",
            "secondary_stat": "secondary_stat",
            "att": "total_att",
            "att_percent": "att_percent",
            "boss_damage": "boss_damage_pct",
            "boss_damage_pct": "boss_damage_pct",
            "damage": "damage_pct",
            "damage_pct": "damage_pct",
            "crit_damage": "crit_damage_pct",
            "final_damage": "final_damage_pct",
        }

        stat_delta = {}
        for k, v in potential_lines.items():
            mapped = key_map.get(k, k)
            if mapped in new_stats:
                new_stats[mapped] = new_stats.get(mapped, 0) + v
                stat_delta[k] = v

        result = cls.estimate_upgrade_cp(char_stats, new_stats, real_cp)
        return {
            "cp_gain": result.get("cp_gain", 0),
            "cp_gain_pct": result.get("cp_gain_pct", 0),
            "estimated_new_cp": result.get("estimated_new_cp", real_cp),
            "margin_low": result.get("margin_low", real_cp),
            "margin_high": result.get("margin_high", real_cp),
            "stat_delta": stat_delta,
        }


    # ── Equipment Analysis ───────────────────────────────────────────────────

    @classmethod
    def analyze_all_equipment(
        cls,
        ap_stats: dict,
        equipped_items: list,
        job_name: str = "",
        real_cp: int = 0,
    ) -> Dict[str, any]:
        """
        Analyze all equipped items and calculate each one's CP contribution.

        Strategy:
          1. Extract character-level stats from apStat (this already reflects all bonuses
             including set effects, because it's the server-side total).
          2. For each item, parse its potential labels to recover flat/% stats.
             Items from the Marketplace API often have NO per-item stats block;
             we must infer from potentials + item weight heuristics.
          3. Distribute set bonuses proportionally to the set members.
          4. Derive per-item CP using marginal decomposition against real_cp.
        """
        char_stats = cls.extract_stats_from_character(ap_stats, job_name)

        # Auto-detect real_cp from attackPower if not provided
        # MSU API: apStat.attackPower IS the Combat Power (전투력), not ATT
        if real_cp <= 0 and isinstance(ap_stats, dict):
            ap_cp_raw = ap_stats.get("attackPower")
            if ap_cp_raw:
                try:
                    real_cp = int(ap_cp_raw)
                except (ValueError, TypeError):
                    pass

        # Pull PAD/MAD from apStat directly (most accurate source)
        # NOTE: attackPower in MSU API is Combat Power (전투력), NOT physical ATT
        ap_pad = _get_stat_total(ap_stats, "pad")
        ap_mad = _get_stat_total(ap_stats, "mad")
        # Use the higher of PAD/MAD (mages use MAD)
        if ap_pad > 0 and char_stats.get("total_att", 0) == 0:
            char_stats["total_att"] = max(ap_pad, ap_mad)
        elif ap_mad > ap_pad and char_stats.get("total_att", 0) < ap_mad:
            char_stats["total_att"] = ap_mad

        # ── Back-calculate ATT from combat_power when pad/mad unavailable ────
        # CP = (4P+S)/100 × ATT × (1+(Dmg+Boss)/100) × (CP_CDM_BASE+CD/100)
        # ATT = CP / [(4P+S)/100 × (1+(Dmg+Boss)/100) × (CP_CDM_BASE+CD/100)]
        cd_base = _get_stat_base(ap_stats, "critical_damage", "criticalDamage")
        if char_stats.get("total_att", 0) == 0 and real_cp > 0:
            stat_comp = cls.calc_stat_component(
                char_stats.get("primary_stat", 0),
                char_stats.get("secondary_stat", 0),
            )
            dmg = cls.calc_damage_mult(
                char_stats.get("damage_pct", 0),
                char_stats.get("boss_damage_pct", 0),
            )
            cd = cls.calc_crit_damage_mult(char_stats.get("crit_damage_pct", 0), cd_base)

            divisor = (stat_comp / 100.0) * dmg * cd
            if divisor > 0:
                back_calc_att = real_cp / divisor
                char_stats["total_att"] = round(back_calc_att, 1)
                print(f"  [CP Engine] Back-calculated ATT={char_stats['total_att']} "
                      f"from CP={real_cp} (stat={stat_comp:.0f}, dmg={dmg:.2f}, cd={cd:.2f})")

        # Store cd_base for marginal decomposition
        char_stats["crit_damage_base"] = cd_base

        primary_key = char_stats.get("primary_key", "str")
        secondary_key = char_stats.get("secondary_key", "dex")

        item_data_list = []
        aggregates = {
            "total_att": 0.0,
            "att_percent": 0.0,
            "primary_pct": 0.0,
            "secondary_pct": 0.0,
            "damage_pct": 0.0,
            "boss_damage_pct": 0.0,
            "final_damage_pct": 0.0,
            "crit_damage_pct": 0.0,
        }

        # ── Detect set membership ──────────────────────────────────────────────
        set_counts: Dict[str, int] = {}
        item_set_names: list = []
        for item in equipped_items:
            item_dict = item if isinstance(item, dict) else item.__dict__ if hasattr(item, '__dict__') else {}
            if item_dict.get("item_type", "") in ("cashEquip", "pet", "arcaneSymbol"):
                item_set_names.append(None)
                continue
            set_name = _detect_set_name(item_dict)
            item_set_names.append(set_name)
            if set_name:
                set_counts[set_name] = set_counts.get(set_name, 0) + 1

        # Compute total set bonus CP for each set
        set_bonus_cp: Dict[str, float] = {}
        for sname, count in set_counts.items():
            set_bonus_cp[sname] = _calc_set_bonus_cp(sname, count, real_cp)

        # ── Build per-item stat list ───────────────────────────────────────────
        set_item_idx: Dict[str, list] = {}  # set_name -> list of indices in item_data_list
        si = 0  # shadow index for item_set_names
        for item in equipped_items:
            item_dict = item if isinstance(item, dict) else item.__dict__ if hasattr(item, '__dict__') else {}
            item_type = item_dict.get("item_type", "")
            if item_type in ("cashEquip", "pet", "arcaneSymbol"):
                si += 1
                continue

            # First try full stat extraction (works when Navigator enriches the item)
            i_stats = extract_item_stats(item_dict, primary_key, secondary_key)

            # If item has no stats at all (Marketplace minimal payload), synthesise
            # from potential labels + slot-level heuristics
            has_real_stats = any(v != 0 for v in i_stats.values())
            if not has_real_stats:
                i_stats = _synthesise_item_stats(
                    item_dict, primary_key, secondary_key,
                    char_stats, real_cp
                )

            idx = len(item_data_list)
            item_data_list.append((item_dict, i_stats, si))

            # Track set membership index
            sname = item_set_names[si] if si < len(item_set_names) else None
            if sname:
                if sname not in set_item_idx:
                    set_item_idx[sname] = []
                set_item_idx[sname].append(idx)

            for k in aggregates:
                aggregates[k] += i_stats.get(k, 0)

            si += 1

        # Bootstrap missing char_stats from aggregated item stats
        for k, v in aggregates.items():
            if char_stats.get(k, 0) == 0 and v > 0:
                char_stats[k] = v

        # Calculate CP using the correct formula
        # NOTE: att_percent=0 because pad.total from the API already includes
        # all %ATT bonuses baked in. Applying att_percent again would double-count.
        # The bootstrapped att_percent is still in char_stats for marginal decomposition.
        total_calc_cp = cls.calculate_cp(
            primary_stat=char_stats["primary_stat"],
            secondary_stat=char_stats["secondary_stat"],
            total_att=char_stats.get("total_att", 0),
            att_percent=0.0,
            damage_pct=char_stats.get("damage_pct", 0),
            boss_damage_pct=char_stats.get("boss_damage_pct", 0),
            crit_damage_pct=char_stats.get("crit_damage_pct", 0),
            crit_damage_base=cd_base,
            total_matt=char_stats.get("total_matt", 0),
        )

        display_cp = real_cp if real_cp > 0 else round(total_calc_cp)

        print(f"DEBUG CP ENGINE [{job_name}]: StatComponent={char_stats['primary_stat']}x4+{char_stats['secondary_stat']}, "
              f"ATT={char_stats.get('total_att')}, realCP={real_cp}, calcCP={round(total_calc_cp)}, displayCP={display_cp}, "
              f"sets={set_counts}")

        items_analysis = []
        for item_dict, i_stats, _si in item_data_list:
            contribution = cls.calculate_item_cp_value(char_stats, i_stats, display_cp)
            items_analysis.append({
                "slot": item_dict.get("slot", ""),
                "name": item_dict.get("name", "Unknown"),
                "item_id": item_dict.get("item_id", 0),
                "starforce": item_dict.get("starforce", 0),
                "potential_grade": item_dict.get("potential_grade", 0),
                "token_id": item_dict.get("token_id"),
                **contribution,
            })

        # ── Distribute set bonus CP evenly among set members ──────────────────
        for sname, idxs in set_item_idx.items():
            bonus = set_bonus_cp.get(sname, 0)
            if bonus > 0 and idxs:
                per_item_bonus = int(bonus / len(idxs))
                for idx in idxs:
                    items_analysis[idx]["cp_contribution"] = (
                        items_analysis[idx].get("cp_contribution", 0) + per_item_bonus
                    )

        # Sort by CP contribution (highest first)
        items_analysis.sort(key=lambda x: x.get("cp_contribution", 0), reverse=True)

        return {
            "calculated_cp": round(total_calc_cp),
            "real_cp": display_cp,
            "character_stats": {
                k: round(v, 1) if isinstance(v, float) else v
                for k, v in char_stats.items()
            },
            "items": items_analysis,
            "total_att": char_stats.get("total_att", 0),
            "total_matt": char_stats.get("total_matt", char_stats.get("magicalAttack", 0)),
        }

    # ── Damage Range Calculation (for reference/display) ──────────────────────

    @classmethod
    def calc_damage_range(
        cls,
        primary_stat: float,
        secondary_stat: float,
        total_att: float,
        damage_pct: float = 0,
        final_damage_pct: float = 0,
        weapon_mult: float = 1.30,
        mastery_pct: float = 90,
    ) -> Dict[str, int]:
        """
        Calculate ATT Range Min/Max (standard damage formula, not CP).

        Max Range = WeaponMult × (4×Primary + Secondary) × (ATT/100) × Damage × FinalDmg
        Min Range = Max Range × (Mastery / 100)
        """
        stat = 4.0 * primary_stat + secondary_stat
        att_factor = total_att / 100.0
        dmg = 1.0 + damage_pct / 100.0
        fd = 1.0 + final_damage_pct / 100.0

        max_range = weapon_mult * stat * att_factor * dmg * fd
        min_range = max_range * (mastery_pct / 100.0)

        return {
            "att_range_max": int(max_range),
            "att_range_min": int(min_range),
            "weapon_mult": weapon_mult,
            "mastery": mastery_pct,
        }


# ─── Set Bonus Tables ────────────────────────────────────────────────────────
#
# MSU / MapleStory N set effects. Values represent the ADDITIONAL CP contribution
# as a fraction of total real_cp, derived empirically.
#
# Format: set_name -> {pieces_required: cp_fraction_added}
# These fractions are calibrated so that a typical endgame character with a full
# Arcane Umbra set sees ~8-10% of their CP coming from set bonuses.
#
SET_BONUS_CP_FRACTION: Dict[str, Dict[int, float]] = {
    # Arcane Umbra (200 set) — 3/5/7 piece effects
    "Arcane Umbra": {3: 0.010, 5: 0.025, 7: 0.050, 8: 0.075},
    # Genesis (240) — strongest set
    "Genesis":      {3: 0.015, 5: 0.035, 7: 0.065, 8: 0.100},
    # Eternal (250)
    "Eternal":      {3: 0.015, 5: 0.035, 7: 0.070, 8: 0.110},
    # AbsoLab (160)
    "AbsoLab":      {3: 0.008, 5: 0.020, 7: 0.040, 8: 0.060},
    # Fafnir (150)
    "Fafnir":       {3: 0.005, 5: 0.012, 7: 0.025, 8: 0.040},
    # Domain (160)
    "Domain":       {3: 0.005, 5: 0.015},
    # Berserked (150)
    "Berserked":    {2: 0.003, 4: 0.008},
    # CRA (150)
    "Chaos Root Abyss": {3: 0.006},
    "Root Abyss":   {3: 0.006},
}

# Item name fragments -> canonical set name
SET_NAME_PATTERNS: Dict[str, str] = {
    "arcane umbra":     "Arcane Umbra",
    "genesis":          "Genesis",
    "eternal":          "Eternal",
    "absolab":          "AbsoLab",
    "abso lab":         "AbsoLab",
    "fafnir":           "Fafnir",
    "domain":           "Domain",
    "berserked":        "Berserked",
    "chaos root abyss": "Chaos Root Abyss",
    "root abyss":       "Root Abyss",
}

# Slot weight table: how much CP each slot typically contributes relative to others.
# Weapon is normalised to 1.0. Used when we have no per-item stat data.
# Sources: community analysis of endgame character teardowns.
SLOT_CP_WEIGHT: Dict[str, float] = {
    "weapon":          1.000,
    "WEAPON":          1.000,
    "emblem":          0.420,   # ATT% potential makes this very high
    "EMBLEM":          0.420,
    "secondary":       0.300,
    "SECONDARY":       0.300,
    "subweapon":       0.300,
    "SUBWEAPON":       0.300,
    "hat":             0.280,
    "HAT":             0.280,
    "cap":             0.280,
    "CAP":             0.280,
    "top":             0.240,
    "TOP":             0.240,
    "clothes":         0.240,
    "CLOTHES":         0.240,
    "shoulder":        0.220,
    "SHOULDER":        0.220,
    "bottom":          0.200,
    "BOTTOM":          0.200,
    "pants":           0.200,
    "PANTS":           0.200,
    "gloves":          0.190,
    "GLOVES":          0.190,
    "cape":            0.180,
    "CAPE":            0.180,
    "shoes":           0.180,
    "SHOES":           0.180,
    "earacc":          0.150,
    "earring":         0.150,
    "EARRING":         0.150,
    "pendant":         0.140,
    "PENDANT":         0.140,
    "pendant1":        0.140,
    "pendant2":        0.130,
    "ring":            0.120,
    "RING":            0.120,
    "ring1":           0.120,
    "ring2":           0.115,
    "ring3":           0.110,
    "ring4":           0.105,
    "belt":            0.130,
    "BELT":            0.130,
    "pocket":          0.100,
    "POCKET":          0.100,
    "badge":           0.090,
    "BADGE":           0.090,
    "medal":           0.050,
    "MEDAL":           0.050,
    "eyeacc":          0.130,
    "EYE ACCESSORY":   0.130,
    "faceacc":         0.120,
    "FACE ACCESSORY":  0.120,
    "faceAccessory":   0.120,
    "eyeAccessory":    0.130,
}


def _detect_set_name(item_dict: dict) -> Optional[str]:
    """Detect which equipment set an item belongs to by name matching."""
    name = (item_dict.get("name") or "").lower()
    for fragment, canonical in SET_NAME_PATTERNS.items():
        if fragment in name:
            return canonical
    return None


def _calc_set_bonus_cp(set_name: str, piece_count: int, real_cp: int) -> float:
    """
    Calculate the additional CP contributed by a set bonus effect.
    Returns absolute CP value (not percentage).
    """
    if real_cp <= 0:
        return 0.0
    tiers = SET_BONUS_CP_FRACTION.get(set_name, {})
    if not tiers:
        return 0.0
    # Find the highest applicable tier
    bonus_frac = 0.0
    for required, frac in sorted(tiers.items()):
        if piece_count >= required:
            bonus_frac = frac
    return real_cp * bonus_frac


# Potential label parser regex patterns (compiled once)
_POT_NUM_RE = _re.compile(
    r'([\+\-]?\d+(?:\.\d+)?)\s*%?',
    _re.IGNORECASE
)
_POT_STAT_RE = _re.compile(
    r'(?P<stat>STR|DEX|INT|LUK|HP|MP|ATT|MAGIC ATT|ATTACK POWER|M\.ATT|ALL STAT|ALL STATS|BOSS(?:\s+DAMAGE)?|DAMAGE|FINAL DAMAGE|CRIT(?:ICAL)? DAMAGE|CRIT(?:ICAL)? RATE|IGNORE (?:DEF|DEFENCE|MONSTER DEFENCE))'  # noqa: E501
    r'[:\s]*([\+\-]?\d+(?:\.\d+)?)\s*(%?)',
    _re.IGNORECASE
)


def _parse_potential_labels(item_dict: dict, primary_key: str, secondary_key: str) -> Dict[str, float]:
    """
    Parse text potential labels and return a stat dict suitable for CP calculation.

    Example labels:
      "STR +12%"  -> primary_pct: 12  (if primary==str)
      "ATT +12%"  -> att_percent: 12
      "DEX +30"   -> secondary_stat: 30  (if secondary==dex)
      "All Stats: +9" -> primary_stat: 9, secondary_stat: 9
      "Boss Damage: +30%" -> boss_damage_pct: 30
    """
    result: Dict[str, float] = {
        "primary_stat": 0.0, "secondary_stat": 0.0,
        "primary_pct": 0.0, "secondary_pct": 0.0,
        "total_att": 0.0, "att_percent": 0.0,
        "damage_pct": 0.0, "boss_damage_pct": 0.0,
        "final_damage_pct": 0.0, "crit_damage_pct": 0.0,
    }

    pkey = primary_key.replace("_stat", "").upper()    # e.g. "STR"
    skey = secondary_key.replace("_stat", "").upper()  # e.g. "DEX"

    # Collect all potential + bonus potential option labels
    labels = []
    for pot_key in ("potential", "bonus_potential"):
        pot = item_dict.get(pot_key) or {}
        if isinstance(pot, dict):
            for opt in pot.values():
                if isinstance(opt, dict):
                    lbl = opt.get("label") or ""
                elif isinstance(opt, str):
                    lbl = opt
                else:
                    lbl = ""
                if lbl:
                    labels.append(lbl.strip())

    for lbl in labels:
        m = _POT_STAT_RE.search(lbl)
        if not m:
            continue
        stat_name = m.group(1).upper().strip()
        try:
            value = float(m.group(2))
        except (ValueError, TypeError):
            continue
        is_pct = bool(m.group(3))

        if stat_name in ("ALL STAT", "ALL STATS"):
            if is_pct:
                result["primary_pct"] += value
                result["secondary_pct"] += value
            else:
                result["primary_stat"] += value
                result["secondary_stat"] += value
        elif stat_name == pkey:
            if is_pct:
                result["primary_pct"] += value
            else:
                result["primary_stat"] += value
        elif stat_name == skey:
            if is_pct:
                result["secondary_pct"] += value
            else:
                result["secondary_stat"] += value
        elif stat_name in ("ATT", "ATTACK POWER", "M.ATT", "MAGIC ATT"):
            if is_pct:
                result["att_percent"] += value
            else:
                result["total_att"] += value
        elif "BOSS" in stat_name:
            result["boss_damage_pct"] += value
        elif "FINAL DAMAGE" in stat_name:
            result["final_damage_pct"] += value
        elif "CRIT" in stat_name and "DAMAGE" in stat_name:
            result["crit_damage_pct"] += value
        elif stat_name == "DAMAGE":
            result["damage_pct"] += value

    return result


def _synthesise_item_stats(
    item_dict: dict,
    primary_key: str,
    secondary_key: str,
    char_stats: Dict[str, float],
    real_cp: int,
) -> Dict[str, float]:
    """
    Build an estimated item stat dict when the API returns no per-item stats.

    Method:
    1. Parse potential labels for exact stats (most accurate).
    2. Estimate base stats from known item-level base stat tables (for flat stats).
    3. Add starforce-based flat stat from SF lookup tables.
    """
    pot_stats = _parse_potential_labels(item_dict, primary_key, secondary_key)

    slot = (item_dict.get("slot") or "").lower()
    item_level = item_dict.get("level") or item_dict.get("required_level") or 0
    starforce = item_dict.get("starforce", 0)

    # -- Base flat stat estimate from item level bracket ---------------------
    # Instead of the old slot-weight × character-total heuristic (which was
    # unreliable), use approximate base stats per item level.
    # These are typical base stats for a clean (no scroll) equip at each tier.
    is_weapon = slot in ("weapon", "WEAPON")

    est_primary, est_secondary, est_att = _estimate_item_base_stats(
        item_level, slot, is_weapon
    )

    # -- Starforce bonus stat ------------------------------------------------
    sf_bonus_stat = 0.0
    sf_bonus_att = 0.0
    if starforce > 0 and item_level > 0:
        sf_gain = get_sf_stat_gain(item_level, 0, starforce, is_weapon=is_weapon)
        sf_bonus_stat = sf_gain.get("cumulative_stat", 0)
        sf_bonus_att  = sf_gain.get("cumulative_att", 0)

    # -- Merge: potential stats dominate; heuristic fills what remains --------
    merged: Dict[str, float] = {
        "primary_stat":     max(pot_stats["primary_stat"],   est_primary + sf_bonus_stat),
        "secondary_stat":   max(pot_stats["secondary_stat"], est_secondary),
        "primary_pct":      pot_stats["primary_pct"],
        "secondary_pct":    pot_stats["secondary_pct"],
        "total_att":        max(pot_stats["total_att"],       est_att + sf_bonus_att),
        "att_percent":      pot_stats["att_percent"],
        "damage_pct":       pot_stats["damage_pct"],
        "boss_damage_pct":  pot_stats["boss_damage_pct"],
        "final_damage_pct": pot_stats["final_damage_pct"],
        "crit_damage_pct":  pot_stats["crit_damage_pct"],
    }
    return merged


# ─── Item Base Stat Estimation Tables ────────────────────────────────────────
# Approximate base stats for a CLEAN equip (no scrolls, no potential, no SF)
# at each item level tier.  These replace the old slot-weight heuristic.
#
# Format: (level_min, level_max) -> (primary_stat, secondary_stat, base_att)
# For armor items, base_att is 0 (armor doesn't give ATT base).
# For weapons, base_att is the weapon's base attack power.
#
_ARMOR_BASE_STAT: List[Tuple[Tuple[int, int], int]] = [
    ((0,   59),   3),
    ((60,  99),   7),
    ((100, 119),  15),
    ((120, 139),  20),
    ((140, 149),  30),   # CRA / Pensalir
    ((150, 159),  40),   # Fafnir armor
    ((160, 179),  45),   # AbsoLab armor
    ((180, 199),  50),
    ((200, 219),  60),   # Arcane Umbra armor
    ((220, 239),  65),
    ((240, 299),  75),   # Genesis / Eternal armor
]

_WEAPON_BASE_ATT: List[Tuple[Tuple[int, int], int]] = [
    ((0,   59),   30),
    ((60,  99),   60),
    ((100, 119),  90),
    ((120, 139),  120),
    ((140, 149),  170),
    ((150, 159),  200),   # Fafnir
    ((160, 179),  180),   # AbsoLab
    ((180, 199),  200),
    ((200, 219),  275),   # Arcane Umbra
    ((220, 239),  300),
    ((240, 299),  320),   # Genesis / Eternal
]


def _estimate_item_base_stats(
    item_level: int, slot: str, is_weapon: bool
) -> Tuple[float, float, float]:
    """
    Estimate an item's base primary stat, secondary stat, and ATT from level.
    Returns (est_primary, est_secondary, est_att).
    """
    if item_level <= 0:
        # No level info — use conservative defaults
        return (20.0, 5.0, 0.0) if not is_weapon else (0.0, 0.0, 100.0)

    # Look up base primary stat from armor table
    base_stat = 10
    for (lo, hi), val in _ARMOR_BASE_STAT:
        if lo <= item_level <= hi:
            base_stat = val
            break
    else:
        if item_level > 240:
            base_stat = 75

    base_att = 0
    if is_weapon:
        for (lo, hi), val in _WEAPON_BASE_ATT:
            if lo <= item_level <= hi:
                base_att = val
                break
        else:
            if item_level > 240:
                base_att = 320

    # Accessories typically have lower base stats than armor
    slot_lower = slot.lower()
    if slot_lower in ("ring", "ring1", "ring2", "ring3", "ring4",
                       "pendant", "pendant1", "pendant2", "earring",
                       "earacc", "eyeacc", "faceacc", "eyeaccessory",
                       "faceaccessory", "belt", "badge", "pocket", "medal"):
        base_stat = int(base_stat * 0.6)

    est_primary = float(base_stat)
    est_secondary = float(max(base_stat // 3, 2))
    est_att = float(base_att)

    return (est_primary, est_secondary, est_att)


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _robust_float(val) -> float:
    """Safely convert API values (which can be dicts, strings, or numbers) to float."""
    if val is None:
        return 0.0
    if isinstance(val, dict):
        # API shape from character wearing: {"total": 88, "base": 40}
        # API shape from character lookup: {"value": 88}
        return _robust_float(val.get("total", val.get("value", 0)))
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _get_stat_total(stats: dict, *keys: str) -> float:
    """Get total value from an AP stats dict, trying multiple key formats."""
    if not stats:
        return 0.0
    for k in keys:
        val = stats.get(k)
        if val is not None:
            return _robust_float(val)
    return 0.0


def _get_stat_base(stats: dict, *keys: str) -> float:
    """Get base value from an AP stats dict (for crit damage base detection)."""
    if not stats:
        return 0.0
    for k in keys:
        val = stats.get(k)
        if val is not None and isinstance(val, dict):
            return float(val.get("base", 0))
    return 0.0


def extract_item_stats(
    item: dict,
    primary_key: str = "str",
    secondary_key: str = "dex",
) -> Dict[str, float]:
    """
    Extract CP-relevant stats from an item's stat block.
    Maps item stat keys to the character's primary/secondary stat keys.

    Item stats format from MSU API:
        stats: { pad: X, mad: X, str: X, dex: X, int: X, luk: X, damr: X, bdr: X, statr: X }
    """
    # Aggressive search for stats/attributes in nested Navigator or Marketplace payloads
    stats_node = item.get("stats") or item.get("data", {}).get("stats")
    if not stats_node and "item" in item:
        stats_node = item["item"].get("stats") or item["item"].get("data", {}).get("stats")
    
    attrs_node = item.get("attributes") or item.get("data", {}).get("attributes")
    if not attrs_node and "item" in item:
        attrs_node = item["item"].get("attributes") or item["item"].get("data", {}).get("attributes")
    
    combined_stats = stats_node if isinstance(stats_node, dict) else {}
    
    # Harvest from attributes array if found (Navigator format)
    if attrs_node and isinstance(attrs_node, list):
        for attr in attrs_node:
            tag = attr.get("tag")
            val = attr.get("value")
            if tag and val is not None:
                combined_stats[tag] = val
                # Normalize common tags to engine-expected keys
                tag_lower = tag.lower()
                if tag == "physicalAttack": combined_stats["pad"] = val
                if tag == "magicalAttack": combined_stats["mad"] = val
                if tag == "damageRate": combined_stats["damr"] = val
                if tag == "bossMonsterDamageRate": combined_stats["bdr"] = val
                if tag == "criticalDamageRate": combined_stats["cdr"] = val
                if "percent" in tag_lower or "rate" in tag_lower:
                     combined_stats[tag_lower.replace("rate", "r").replace("percent", "r")] = val
                     
    if not combined_stats:
        return {
            "primary_stat": 0, "secondary_stat": 0, "total_att": 0,
            "att_percent": 0, "damage_pct": 0, "boss_damage_pct": 0,
            "final_damage_pct": 0, "crit_damage_pct": 0,
        }

    stats = combined_stats

    # Map primary/secondary key to item stat keys
    prim_stat_key = primary_key.replace("_stat", "")  # "str_stat" -> "str"
    sec_stat_key = secondary_key.replace("_stat", "")

    def _val(keys, default=0.0):
        for k in keys:
            v = stats.get(k)
            if v is not None:
                return _robust_float(v)
        return default

    # Primary/Secondary flat stats
    primary_val = _val([prim_stat_key, f"{prim_stat_key}_stat", f"{prim_stat_key}Stat"])
    secondary_val = _val([sec_stat_key, f"{sec_stat_key}_stat", f"{sec_stat_key}Stat"])

    # Stats from potential/bonus lines (percent and other aliases)
    prim_pct = _val([f"{prim_stat_key}r", f"{prim_stat_key}_percent", f"{prim_stat_key}_rate", "strr" if prim_stat_key=="str" else "dexr"])
    sec_pct = _val([f"{sec_stat_key}r", f"{sec_stat_key}_percent", f"{sec_stat_key}_rate", "lukr" if sec_stat_key=="luk" else "intr"])

    # All Stat flat and percent
    all_stat = _val(["all_stat", "allStat", "all_stat_flat"])
    all_stat_pct = _val(["statr", "allStat_percent", "all_stat_rate", "all_stat_percent"])

    # Attack (PAD for physical, MAD for magical, totalAtt as alternative)
    att = _val(["pad", "mad", "attack", "att", "physical_attack", "magical_attack", "physicalAttack", "magicalAttack", "total_attack", "totalAtt", "pad_rate", "atp"])

    # Attack % 
    att_pct = _val(["atp", "att_percent", "attack_percent", "attack_rate", "padr", "madr"])

    # Damage metrics
    dmg_pct = _val(["damr", "damage_percent", "damage_rate", "dmgr"])
    boss_pct = _val(["bdr", "boss_damage_percent", "boss_damage_rate", "boss_monster_damage"])
    cd_pct = _val(["cdr", "crit_damage_percent", "critical_damage", "criticalDamage"])
    fd_pct = _val(["fdr", "final_damage_percent", "finalDamage"])

    return {
        "primary_stat": primary_val + all_stat,
        "secondary_stat": secondary_val + all_stat,
        "primary_pct": prim_pct + all_stat_pct,
        "secondary_pct": sec_pct + all_stat_pct,
        "total_att": att,
        "att_percent": att_pct,
        "damage_pct": dmg_pct,
        "boss_damage_pct": boss_pct,
        "final_damage_pct": fd_pct,
        "crit_damage_pct": cd_pct,
    }


# Singleton
combat_power_engine = CombatPowerEngine()
