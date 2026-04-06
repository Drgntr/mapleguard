"""
MSU Legion Bonus Calculator.

In MapleStory Universe, the Legion system grants stat bonuses based on the total
block count of all characters on your account deployed to the Legion grid.

Each character contributes blocks based on their level:
  Lv280+ = 10 blocks, Lv250-279 = 7 blocks, Lv200-249 = 4 blocks,
  Lv140-199 = 3 blocks, Lv100-139 = 2 blocks, Lv60-99 = 1 block.

Total blocks map to milestones that grant permanent stat bonuses.
"""

# Legion block milestones and their bonuses
LEGION_TIERS = {
    30:  {"str_pct": 10, "dex_pct": 10, "int_pct": 10, "luk_pct": 10},
    60:  {"str_pct": 11, "dex_pct": 11, "int_pct": 11, "luk_pct": 11},
    90:  {"str_pct": 13, "dex_pct": 13, "int_pct": 13, "luk_pct": 13},
    120: {"str_pct": 14, "dex_pct": 14, "int_pct": 14, "luk_pct": 14},
    150: {"str_pct": 15, "dex_pct": 15, "int_pct": 15, "luk_pct": 15},
    180: {"str_pct": 17, "dex_pct": 17, "int_pct": 17, "luk_pct": 17},
    210: {"str_pct": 18, "dex_pct": 18, "int_pct": 18, "luk_pct": 18, "damage_percent": 3},
    240: {"str_pct": 19, "dex_pct": 19, "int_pct": 19, "luk_pct": 19, "damage_percent": 4},
    270: {"str_pct": 20, "dex_pct": 20, "int_pct": 20, "luk_pct": 20, "damage_percent": 5},
    300: {"str_pct": 20, "dex_pct": 20, "int_pct": 20, "luk_pct": 20, "damage_percent": 8, "boss_monster_damage_percent": 8},
    330: {"str_pct": 20, "dex_pct": 20, "int_pct": 20, "luk_pct": 20, "damage_percent": 9, "boss_monster_damage_percent": 10},
    360: {"str_pct": 20, "dex_pct": 20, "int_pct": 20, "luk_pct": 20, "damage_percent": 11, "boss_monster_damage_percent": 12},
    400: {"str_pct": 20, "dex_pct": 20, "int_pct": 20, "luk_pct": 20, "damage_percent": 12, "boss_monster_damage_percent": 15},
    420: {"str_pct": 20, "dex_pct": 20, "int_pct": 20, "luk_pct": 20, "damage_percent": 14, "boss_monster_damage_percent": 18},
    440: {"str_pct": 20, "dex_pct": 20, "int_pct": 20, "luk_pct": 20, "damage_percent": 15, "boss_monster_damage_percent": 20},
    460: {"str_pct": 20, "dex_pct": 20, "int_pct": 20, "luk_pct": 20, "damage_percent": 15, "boss_monster_damage_percent": 25, "critical_damage_percent": 1},
    500: {"str_pct": 20, "dex_pct": 20, "int_pct": 20, "luk_pct": 20, "damage_percent": 15, "boss_monster_damage_percent": 25, "critical_damage_percent": 2},
    550: {"str_pct": 30, "dex_pct": 30, "int_pct": 30, "luk_pct": 30, "damage_percent": 18, "boss_monster_damage_percent": 28, "critical_damage_percent": 2},
    600: {"str_pct": 30, "dex_pct": 30, "int_pct": 30, "luk_pct": 30, "damage_percent": 20, "boss_monster_damage_percent": 30, "critical_damage_percent": 3},
}

# Character level to legion block mapping
LEVEL_TO_BLOCKS = [
    (270, 10),
    (250, 7),
    (200, 4),
    (140, 3),
    (100, 2),
    (60, 1),
]


def character_to_legion_blocks(level: int) -> int:
    """Convert character level to legion block contribution."""
    for min_level, blocks in LEVEL_TO_BLOCKS:
        if level >= min_level:
            return blocks
    return 0


def _merge_stats(stats_list: list[dict]) -> dict:
    """Merge cumulative stats from multiple tier milestones (highest value per stat wins)."""
    merged: dict[str, float] = {}
    for stats in stats_list:
        for key, val in stats.items():
            merged[key] = max(merged.get(key, 0), val)
    return merged


def calculate_legion_bonus(total_blocks: int) -> dict:
    """Calculate legion stat bonuses for a given total block count."""
    if total_blocks <= 0:
        return {}

    applicable = []
    for tier_blocks, stats in sorted(LEGION_TIERS.items(), key=lambda x: x[0]):
        if total_blocks >= tier_blocks:
            applicable.append(stats)
        if tier_blocks > total_blocks + 50:
            break

    if not applicable:
        # Below first tier
        return {}

    result = _merge_stats(applicable)
    result["total_blocks"] = total_blocks

    # Find next tier info
    next_tier = None
    for tier_blocks in sorted(LEGION_TIERS.keys()):
        if total_blocks < tier_blocks:
            next_tier = {"threshold": tier_blocks, "blocks_needed": tier_blocks - total_blocks}
            break

    if next_tier:
        result["next_tier"] = next_tier

    return result


def get_legion_tier_milestones() -> list[dict]:
    """Return all legion tier thresholds and their bonuses for display."""
    return [
        {"threshold": tb, "bonuses": stats}
        for tb, stats in sorted(LEGION_TIERS.items())
    ]
