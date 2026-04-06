from typing import List, Dict

# Comprehensive curated catalog of high-tier MapleStory N items
ITEM_CATALOG = [
    # ── Arcane Umbra (Level 200) ──────────────────────────────────────────────
    {"item_id": 1602000, "name": "Arcane Umbra Knight Hat", "level": 200, "slot": "HAT"},
    {"item_id": 1602001, "name": "Arcane Umbra Mage Hat", "level": 200, "slot": "HAT"},
    {"item_id": 1602002, "name": "Arcane Umbra Archer Hat", "level": 200, "slot": "HAT"},
    {"item_id": 1602003, "name": "Arcane Umbra Thief Hat", "level": 200, "slot": "HAT"},
    {"item_id": 1602004, "name": "Arcane Umbra Pirate Hat", "level": 200, "slot": "HAT"},
    {"item_id": 1602005, "name": "Arcane Umbra Knight Suit", "level": 200, "slot": "TOP"},
    {"item_id": 1602006, "name": "Arcane Umbra Mage Suit", "level": 200, "slot": "TOP"},
    {"item_id": 1602007, "name": "Arcane Umbra Archer Suit", "level": 200, "slot": "TOP"},
    {"item_id": 1602008, "name": "Arcane Umbra Thief Suit", "level": 200, "slot": "TOP"},
    {"item_id": 1602009, "name": "Arcane Umbra Pirate Suit", "level": 200, "slot": "TOP"},
    {"item_id": 1602010, "name": "Arcane Umbra Knight Shoes", "level": 200, "slot": "SHOES"},
    {"item_id": 1602015, "name": "Arcane Umbra Knight Gloves", "level": 200, "slot": "GLOVES"},
    {"item_id": 1602020, "name": "Arcane Umbra Knight Cape", "level": 200, "slot": "CAPE"},
    {"item_id": 1602025, "name": "Arcane Umbra Knight Shoulder", "level": 200, "slot": "SHOULDER"},

    # ── Eternal (Level 250) ───────────────────────────────────────────────────
    {"item_id": 1602500, "name": "Eternal Knight Hat", "level": 250, "slot": "HAT"},
    {"item_id": 1602501, "name": "Eternal Mage Hat", "level": 250, "slot": "HAT"},
    {"item_id": 1602505, "name": "Eternal Knight Suit", "level": 250, "slot": "TOP"},
    {"item_id": 1602510, "name": "Eternal Knight Bottom", "level": 250, "slot": "BOTTOM"},
    {"item_id": 1602515, "name": "Eternal Knight Shoes", "level": 250, "slot": "SHOES"},
    {"item_id": 1602520, "name": "Eternal Knight Gloves", "level": 250, "slot": "GLOVES"},
    {"item_id": 1602525, "name": "Eternal Knight Cape", "level": 250, "slot": "CAPE"},

    # ── AbsoLab (Level 160) ───────────────────────────────────────────────────
    {"item_id": 1152200, "name": "AbsoLab Knight Hat", "level": 160, "slot": "HAT"},
    {"item_id": 1152205, "name": "AbsoLab Knight Suit", "level": 160, "slot": "TOP"},
    {"item_id": 1152210, "name": "AbsoLab Knight Shoes", "level": 160, "slot": "SHOES"},
    {"item_id": 1152215, "name": "AbsoLab Knight Gloves", "level": 160, "slot": "GLOVES"},
    {"item_id": 1152220, "name": "AbsoLab Knight Cape", "level": 160, "slot": "CAPE"},
    {"item_id": 1152225, "name": "AbsoLab Knight Shoulder", "level": 160, "slot": "SHOULDER"},

    # ── Fafnir Weapons (Level 150) ────────────────────────────────────────────
    {"item_id": 1302800, "name": "Fafnir Damascus", "level": 150, "slot": "WEAPON"},
    {"item_id": 1302801, "name": "Fafnir Kaleido", "level": 150, "slot": "WEAPON"},
    {"item_id": 1312800, "name": "Fafnir Axe", "level": 150, "slot": "WEAPON"},
    {"item_id": 1322800, "name": "Fafnir Mace", "level": 150, "slot": "WEAPON"},
    {"item_id": 1332800, "name": "Fafnir Cutlass", "level": 150, "slot": "WEAPON"},
    {"item_id": 1342800, "name": "Fafnir Bow Heroic", "level": 150, "slot": "WEAPON"},
    {"item_id": 1362800, "name": "Fafnir Hunter Bow", "level": 150, "slot": "WEAPON"},
    {"item_id": 1372800, "name": "Fafnir Sand Charm", "level": 150, "slot": "WEAPON"},
    {"item_id": 1382800, "name": "Fafnir Umbra Staff", "level": 150, "slot": "WEAPON"},
    {"item_id": 1392800, "name": "Fafnir Wristbands", "level": 150, "slot": "WEAPON"},
    {"item_id": 1402800, "name": "Fafnir Chain", "level": 150, "slot": "WEAPON"},
    {"item_id": 1412800, "name": "Fafnir Soul Shooter", "level": 150, "slot": "WEAPON"},
    {"item_id": 1422800, "name": "Fafnir Fan", "level": 150, "slot": "WEAPON"},
    {"item_id": 1432800, "name": "Fafnir Cannon Shooter", "level": 150, "slot": "WEAPON"},
    {"item_id": 1442800, "name": "Fafnir Desperado", "level": 150, "slot": "WEAPON"},
    {"item_id": 1452800, "name": "Fafnir Long Sword", "level": 150, "slot": "WEAPON"},
    {"item_id": 1472800, "name": "Fafnir Kerises", "level": 150, "slot": "WEAPON"},
    {"item_id": 1482800, "name": "Fafnir Luck Double Axe", "level": 150, "slot": "WEAPON"},
    {"item_id": 1492800, "name": "Fafnir Pernium Whip", "level": 150, "slot": "WEAPON"},
    {"item_id": 1212800, "name": "Fafnir Wand", "level": 150, "slot": "WEAPON"},
    {"item_id": 1222800, "name": "Fafnir Staff", "level": 150, "slot": "WEAPON"},

    # ── Arcane Weapons (Level 200) ────────────────────────────────────────────
    {"item_id": 1302000, "name": "Arcane Umbra Saber", "level": 200, "slot": "WEAPON"},
    {"item_id": 1332000, "name": "Arcane Umbra Dagger", "level": 200, "slot": "WEAPON"},
    {"item_id": 1212000, "name": "Arcane Umbra Wand", "level": 200, "slot": "WEAPON"},
    {"item_id": 1222000, "name": "Arcane Umbra Staff", "level": 200, "slot": "WEAPON"},
    {"item_id": 1402000, "name": "Arcane Umbra Chain", "level": 200, "slot": "WEAPON"},
    {"item_id": 1432000, "name": "Arcane Umbra Cannon", "level": 200, "slot": "WEAPON"},

    # ── Pitched Boss Set ──────────────────────────────────────────────────────
    {"item_id": 1012000, "name": "Magic Eyepatch", "level": 160, "slot": "EYE_ACC"},
    {"item_id": 1022000, "name": "Dreamy Belt", "level": 200, "slot": "BELT"},
    {"item_id": 1032000, "name": "Berserked", "level": 160, "slot": "PENDANT"},
    {"item_id": 1122000, "name": "Source of Suffering", "level": 160, "slot": "RING"},
    {"item_id": 1132000, "name": "Commanding Force Earring", "level": 200, "slot": "EARRING"},
    {"item_id": 1113000, "name": "Endless Terror", "level": 200, "slot": "RING"},
    {"item_id": 1142000, "name": "Mythic Familiar Ring", "level": 200, "slot": "RING"},

    # ── Boss Accessory Set ────────────────────────────────────────────────────
    {"item_id": 1114017, "name": "Condensed Power Crystal", "level": 120, "slot": "FACE_ACC"},
    {"item_id": 1012433, "name": "Aquatic Letter Eye Accessory", "level": 120, "slot": "EYE_ACC"},
    {"item_id": 1032272, "name": "Silver Blossom Ring", "level": 120, "slot": "RING"},
    {"item_id": 1032271, "name": "Noble Ifia's Ring", "level": 120, "slot": "RING"},
    {"item_id": 1032273, "name": "Guardian Angel Ring", "level": 120, "slot": "RING"},
    {"item_id": 1032081, "name": "Mechanator Pendant", "level": 120, "slot": "PENDANT"},
    {"item_id": 1103043, "name": "Dominator Pendant", "level": 160, "slot": "PENDANT"},
    {"item_id": 1082545, "name": "Golden Clover Belt", "level": 110, "slot": "BELT"},
    {"item_id": 1082002, "name": "Enraged Zakum Belt", "level": 130, "slot": "BELT"},
    {"item_id": 1102140, "name": "Royal Black Metal Shoulder", "level": 150, "slot": "SHOULDER"},
    {"item_id": 1162009, "name": "Pink Holy Cup", "level": 140, "slot": "POCKET"},
    {"item_id": 1162061, "name": "Stone of Eternal Life", "level": 140, "slot": "POCKET"},
    {"item_id": 1182087, "name": "Crystal Ventus Badge", "level": 110, "slot": "BADGE"},

    # ── Sweetwater & Superior Gollux ──────────────────────────────────────────
    {"item_id": 1122150, "name": "Superior Gollux Ring", "level": 150, "slot": "RING"},
    {"item_id": 1132246, "name": "Superior Gollux Belt", "level": 150, "slot": "BELT"},
    {"item_id": 1122267, "name": "Superior Gollux Pendant", "level": 150, "slot": "PENDANT"},
    {"item_id": 1032223, "name": "Superior Gollux Earring", "level": 150, "slot": "EARRING"},
    {"item_id": 1113070, "name": "Reinforced Gollux Ring", "level": 140, "slot": "RING"},
    {"item_id": 1132245, "name": "Reinforced Gollux Belt", "level": 140, "slot": "BELT"},
    {"item_id": 1122266, "name": "Reinforced Gollux Pendant", "level": 140, "slot": "PENDANT"},
    {"item_id": 1032222, "name": "Reinforced Gollux Earring", "level": 140, "slot": "EARRING"},

    # ── Dawn Boss Set ─────────────────────────────────────────────────────────
    {"item_id": 1022278, "name": "Twilight Mark", "level": 140, "slot": "FACE_ACC"},
    {"item_id": 1032316, "name": "Estella Earring", "level": 160, "slot": "EARRING"},
    {"item_id": 1113306, "name": "Daybreak Pendant", "level": 140, "slot": "PENDANT"},
    {"item_id": 1114305, "name": "Guardian Angel Ring", "level": 160, "slot": "RING"},

    # ── More Arcane Umbra (Level 200) ──────────────────────────────────────────
    {"item_id": 1472252, "name": "Arcane Umbra Guards", "level": 200, "slot": "WEAPON"},
    {"item_id": 1482220, "name": "Arcane Umbra Knuckle", "level": 200, "slot": "WEAPON"},
    {"item_id": 1492235, "name": "Arcane Umbra Pistol", "level": 200, "slot": "WEAPON"},
    {"item_id": 1382223, "name": "Arcane Umbra Staff", "level": 200, "slot": "WEAPON"},
    {"item_id": 1372223, "name": "Arcane Umbra Wand", "level": 200, "slot": "WEAPON"},
    {"item_id": 1302328, "name": "Arcane Umbra Two-handed Sword", "level": 200, "slot": "WEAPON"},
    {"item_id": 1452257, "name": "Arcane Umbra Longbow", "level": 200, "slot": "WEAPON"},
    {"item_id": 1462241, "name": "Arcane Umbra Crossbow", "level": 200, "slot": "WEAPON"},
    {"item_id": 1342104, "name": "Arcane Umbra Dual Bowguns", "level": 200, "slot": "WEAPON"},
    {"item_id": 1402253, "name": "Arcane Umbra Polearm", "level": 200, "slot": "WEAPON"},
    {"item_id": 1432218, "name": "Arcane Umbra Spear", "level": 200, "slot": "WEAPON"},
    {"item_id": 1322255, "name": "Arcane Umbra Mace", "level": 200, "slot": "WEAPON"},
    {"item_id": 1312203, "name": "Arcane Umbra One-handed Axe", "level": 200, "slot": "WEAPON"},
    {"item_id": 1332279, "name": "Arcane Umbra Dagger", "level": 200, "slot": "WEAPON"},

    # ── Eternal (Level 250) ───────────────────────────────────────────────────
    {"item_id": 1005980, "name": "Eternal Thief Hat", "level": 250, "slot": "HAT"},
    {"item_id": 1053733, "name": "Eternal Thief Suit", "level": 250, "slot": "TOP"},
    {"item_id": 1063266, "name": "Eternal Thief Pants", "level": 250, "slot": "BOTTOM"},

    # ── Root Abyss Set (Fafnir Gear) ──────────────────────────────────────────
    {"item_id": 1003797, "name": "Fafnir Royal Assassin Hood", "level": 150, "slot": "HAT"},
    {"item_id": 1052595, "name": "Eagle Eye Assassin Shirt", "level": 150, "slot": "TOP"},
    {"item_id": 1062161, "name": "Trixter Assassin Pants", "level": 150, "slot": "BOTTOM"},
]


class ItemCatalogService:
    def __init__(self):
        # Build a lowercase search index for fast queries
        self._index = [(item["name"].lower(), item) for item in ITEM_CATALOG]

    def get_catalog(self, query: str = "") -> List[Dict]:
        if not query:
            return ITEM_CATALOG[:24]

        q = query.lower()
        # Prioritize items where query starts a word in the name
        primary = [item for name, item in self._index if q in name or q in str(item["item_id"])]
        return primary[:12]

    def get_by_id(self, item_id: int) -> Dict | None:
        for item in ITEM_CATALOG:
            if item["item_id"] == item_id:
                return item
        return None


catalog_service = ItemCatalogService()
