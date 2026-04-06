"""
Collection Bonus Calculator.

In MapleStory Universe, the Collection system grants permanent stat bonuses
as your account's collection score increases. Each character contributes a
score based on their level.

Collection milestones grant progressively better bonuses.
"""

# Collection milestones and their bonuses
COLLECTION_TIERS = {
    1000: {"ignore_defence_percent": 10},
    2000: {"ignore_defence_percent": 15},
    3000: {"ignore_defence_percent": 20},
    4000: {"boss_monster_damage_percent": 10},
    5000: {"boss_monster_damage_percent": 15},
    6000: {"boss_monster_damage_percent": 20},
    7000: {"boss_monster_damage_percent": 25},
    8000: {"critical_damage_percent": 1},
    9000: {"critical_damage_percent": 2},
    10000: {"critical_damage_percent": 3, "boss_monster_damage_percent": 30},
    15000: {"critical_damage_percent": 3, "boss_monster_damage_percent": 35, "damage_percent": 5},
    20000: {"critical_damage_percent": 3, "boss_monster_damage_percent": 35, "damage_percent": 10},
    25000: {"critical_damage_percent": 4, "boss_monster_damage_percent": 35, "damage_percent": 15},
    30000: {"critical_damage_percent": 4, "boss_monster_damage_percent": 40, "damage_percent": 20},
}

# Character level to collection score mapping
LEVEL_TO_SCORE = [
    (260, 1000),
    (250, 800),
    (240, 600),
    (230, 450),
    (220, 350),
    (210, 300),
    (200, 250),
    (190, 200),
    (180, 150),
    (170, 120),
    (160, 100),
    (150, 80),
    (140, 60),
    (120, 40),
    (100, 20),
]


def character_to_collection_score(level: int) -> int:
    """Convert character level to collection score contribution."""
    for min_level, score in LEVEL_TO_SCORE:
        if level >= min_level:
            return score
    return 10


def _merge_stats(stats_list: list[dict]) -> dict:
    """Merge cumulative stats from milestones (highest value per stat wins)."""
    merged: dict[str, float] = {}
    for stats in stats_list:
        for key, val in stats.items():
            merged[key] = max(merged.get(key, 0), val)
    return merged


def calculate_collection_bonus(total_score: int) -> dict:
    """Calculate collection stat bonuses for a given total collection score."""
    if total_score <= 0:
        return {}

    applicable = []
    for tier_score, stats in sorted(COLLECTION_TIERS.items(), key=lambda x: x[0]):
        if total_score >= tier_score:
            applicable.append(stats)

    if not applicable:
        return {}

    result = _merge_stats(applicable)
    result["total_score"] = total_score

    # Find next tier
    next_tier = None
    for tier_score in sorted(COLLECTION_TIERS.keys()):
        if total_score < tier_score:
            next_tier = {"threshold": tier_score, "score_needed": tier_score - total_score}
            break

    if next_tier:
        result["next_tier"] = next_tier

    return result


def get_collection_milestones() -> list[dict]:
    """Return all collection milestones and their bonuses for display."""
    return [
        {"threshold": ts, "bonuses": stats}
        for ts, stats in sorted(COLLECTION_TIERS.items())
    ]
