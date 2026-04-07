from pydantic import BaseModel, computed_field, model_validator
from typing import Optional
from datetime import datetime


class ApStat(BaseModel):
    total: float = 0
    base: float = 0
    enhance: float = 0


class ApStats(BaseModel):
    str_stat: ApStat = ApStat()
    dex: ApStat = ApStat()
    int_stat: ApStat = ApStat()
    luk: ApStat = ApStat()
    hp: ApStat = ApStat()
    mp: ApStat = ApStat()
    pad: ApStat = ApStat()          # Physical Attack (ATT)
    mad: ApStat = ApStat()          # Magical Attack (MATT)
    damage: ApStat = ApStat()
    boss_monster_damage: ApStat = ApStat()
    final_damage: ApStat = ApStat()
    ignore_defence: ApStat = ApStat()
    critical_rate: ApStat = ApStat()
    critical_damage: ApStat = ApStat()
    buff_duration_rate: ApStat = ApStat()
    abnormal_status_resistance: ApStat = ApStat()
    defence: ApStat = ApStat()
    speed: ApStat = ApStat()
    jump: ApStat = ApStat()
    knockback_resistance: ApStat = ApStat()
    combat_power: ApStat = ApStat()

    @staticmethod
    def from_api(raw: dict) -> "ApStats":
        def _stat(*keys: str) -> ApStat:
            """Try multiple camelCase and snake_case key variants."""
            for k in keys:
                s = raw.get(k)
                if s is None:
                    continue
                if isinstance(s, dict):
                    return ApStat(
                        total=s.get("total", 0),
                        base=s.get("base", 0),
                        enhance=s.get("enhance", 0),
                    )
                if isinstance(s, (int, float)):
                    return ApStat(total=s, base=s, enhance=0)
                if isinstance(s, str):
                    try:
                        v = float(s)
                        return ApStat(total=v, base=v, enhance=0)
                    except (ValueError, TypeError):
                        pass
            return ApStat()
        return ApStats(
            str_stat=_stat("str"),
            dex=_stat("dex"),
            int_stat=_stat("int"),
            luk=_stat("luk"),
            hp=_stat("hp"),
            mp=_stat("mp"),
            pad=_stat("pad", "physicalAttack", "attackPower"),
            mad=_stat("mad", "magicalAttack", "magicAttack"),
            damage=_stat("damage"),
            boss_monster_damage=_stat("bossMonsterDamage", "boss_monster_damage"),
            final_damage=_stat("finalDamage", "final_damage"),
            ignore_defence=_stat("ignoreDefence", "ignore_defence"),
            critical_rate=_stat("criticalRate", "critical_rate"),
            critical_damage=_stat("criticalDamage", "critical_damage"),
            buff_duration_rate=_stat("buffDurationRate", "buff_duration_rate"),
            abnormal_status_resistance=_stat("abnormalStatusResistance", "abnormal_status_resistance"),
            defence=_stat("defence"),
            speed=_stat("speed"),
            jump=_stat("jump"),
            knockback_resistance=_stat("knockbackResistance", "knockback_resistance"),
            combat_power=_stat("combatPower", "combat_power"),
        )


class EquippedItem(BaseModel):
    slot: str = ""
    item_type: str = ""  # equip, cashEquip, pet, arcaneSymbol
    item_id: int = 0
    name: Optional[str] = None
    token_id: Optional[str] = None
    mintable: bool = False
    starforce: int = 0
    potential_grade: int = 0
    potential: Optional[dict] = None
    bonus_potential: Optional[dict] = None
    stats: Optional[dict] = None
    image_url: Optional[str] = None
    level: int = 0
    exp: int = 0
    max_exp: int = 0
    force: int = 0


class CharacterListing(BaseModel):
    token_id: str
    name: str
    class_name: str = ""
    job_name: str = ""
    class_code: int = 0
    job_code: int = 0
    level: int = 0
    price_wei: str = "0"
    created_at: Optional[datetime] = None
    nesolet_wei: Optional[str] = None
    ap_stats: Optional[ApStats] = None
    asset_key: Optional[str] = None
    seller: Optional[str] = None
    image_url: Optional[str] = None
    nickname: Optional[str] = None
    equipped_items: list[EquippedItem] = []
    mintable_count: int = 0
    hyper_stats: dict[str, int] = {}
    ability_grades: list[int] = []
    char_cp: Optional[float] = 0.0
    char_att: Optional[float] = 0.0
    char_matt: Optional[float] = 0.0

    @model_validator(mode='after')
    def unify_names(self) -> 'CharacterListing':
        if not self.nickname and self.name:
            self.nickname = self.name
        elif not self.name and self.nickname:
            self.name = self.nickname
        return self

    @computed_field
    @property
    def price(self) -> float:
        try:
            return int(self.price_wei) / 1e18
        except (ValueError, TypeError):
            return 0.0

    @computed_field
    @property
    def nesolet(self) -> float:
        try:
            return int(self.nesolet_wei or "0") / 1e18
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def from_explore_api(raw: dict) -> "CharacterListing":
        """Parse from /marketplace/explore/characters response.
        New API shape (2026-03): character info is inside 'character.common' + 'character.common.job'.
        """
        sales = raw.get("salesInfo", {})
        char_block = raw.get("character", {})
        common = char_block.get("common", {})
        job = common.get("job", {}) or raw.get("data", {}).get("job", {})
        level = common.get("level", 0) or raw.get("data", {}).get("level", 0)

        # The explore API doesn't populate className/jobName — use category tiers instead
        cat = raw.get("category", {})
        tier3_label = cat.get("tier3", {}).get("label", "")
        tier2_label = cat.get("tier2", {}).get("label", "")
        class_name = tier3_label or job.get("className", "") or tier2_label or ""
        job_name = job.get("jobName", "")

        return CharacterListing(
            token_id=str(raw.get("tokenId", "")),
            name=raw.get("name", ""),
            class_name=class_name,
            job_name=job_name,
            class_code=job.get("classCode", 0),
            job_code=job.get("jobCode", 0),
            level=level,
            price_wei=str(sales.get("priceWei", "0")),
            created_at=sales.get("createdAt"),
            image_url=raw.get("imageUrl"),
            asset_key=raw.get("assetKey"),
        )

    @staticmethod
    def from_recent_api(raw: dict) -> "CharacterListing":
        """Parse from /dashboard/recently-listed (character type)."""
        char = raw.get("character", {})
        sales = raw.get("salesInfo", {})
        job = char.get("job", {})
        return CharacterListing(
            token_id=str(raw.get("tokenId", "")),
            name=raw.get("name", ""),
            class_name=job.get("className", ""),
            job_name=job.get("jobName", ""),
            class_code=job.get("classCode", 0),
            job_code=job.get("jobCode", 0),
            level=char.get("level", 0),
            price_wei=str(sales.get("priceWei", "0")),
            created_at=sales.get("createdAt"),
            image_url=raw.get("imageUrl"),
        )

    @staticmethod
    def _get_name(slot_obj):
        GENERIC_SLOTS = {"HAT", "TOP", "BOTTOM", "SHOES", "GLOVES", "CAPE", "WEAPON", "SECONDARY",
                         "SUBWEAPON", "FACE ACC", "EYE ACC", "EARRING", "SHOULDER", "BELT",
                         "POCKET", "BADGE", "EMBLEM", "RING", "PENDANT"}
        for k in ["name", "itemName", "item_name"]:
            v = slot_obj.get(k) or slot_obj.get("common", {}).get(k)
            if v and isinstance(v, str) and v.upper() not in GENERIC_SLOTS:
                return v
        return None

    @staticmethod
    def _parse_pot(pot_raw):
        if not pot_raw: return None
        opts = {}
        for k in ["option1", "option2", "option3"]:
            o = pot_raw.get(k, {})
            if isinstance(o, dict):
                lbl = o.get("label") or o.get("optionName")
                if lbl:
                    opts[k] = {"label": lbl, "grade": o.get("grade", 0)}
        return opts if opts else None

    @staticmethod
    def _find_grade(obj):
        if not obj: return 0
        deep_grade = obj.get("enhance", {}).get("potential", {}).get("option1", {}).get("grade")
        if deep_grade:
            return deep_grade
        for k in ["potentialGrade", "potential_grade", "potential", "grade"]:
            v = obj.get(k)
            if isinstance(v, int) and v > 0:
                return v
            if isinstance(v, str):
                try: return int(v)
                except: pass
        return 0

    @staticmethod
    def _get_sf_deep(obj):
        if not obj: return 0
        return obj.get("enhance", {}).get("starforce", {}).get("enhanced") or 0

    @staticmethod
    def from_detail_api(data: dict) -> "CharacterListing":
        """Parse from /marketplace/marketplace/characters/{tokenId} detail response.
        New API shape (2026-03): top-level dict has tokenId, name, imageUrl, assetKey,
        salesInfo, and 'character' block with common/apStat/wearing.
        """
        char = data.get("character", {})
        common = char.get("common", {})
        sales = data.get("salesInfo", {})
        job = common.get("job", {})
        wearing = char.get("wearing", {})



        # Parse equipped items
        equipped = []
        mintable_count = 0

        # Standard Equipment (equip dict), Cash, Pets
        for item_type in ("equip", "cashEquip", "pet"):
            slots = wearing.get(item_type, {})
            if not isinstance(slots, dict):
                continue
            for slot_name, slot_data in slots.items():
                if not isinstance(slot_data, dict) or not slot_data:
                    continue
                # In the new minimal API shape, slot_data IS the item object directly
                item_obj = slot_data.get("item") or slot_data.get("data") or slot_data

                ei = EquippedItem(
                    slot=slot_name,
                    item_type=item_type,
                    item_id=item_obj.get("itemId", 0) or item_obj.get("common", {}).get("itemId", 0),
                    name=CharacterListing._get_name(item_obj),
                    token_id=item_obj.get("tokenId") or item_obj.get("assetKey"),
                    mintable=bool(item_obj.get("mintable") or item_obj.get("isMinted")),
                    potential_grade=CharacterListing._find_grade(item_obj),
                    starforce=(item_obj.get("enhance", {}).get("starforce", {}).get("enhanced")
                               or item_obj.get("starforce", 0)),
                    potential=CharacterListing._parse_pot(
                        item_obj.get("enhance", {}).get("potential")
                        or item_obj.get("potential")
                    ),
                    bonus_potential=CharacterListing._parse_pot(
                        item_obj.get("enhance", {}).get("bonusPotential")
                        or item_obj.get("bonusPotential")
                    ),
                    stats=item_obj.get("stats"),
                    image_url=item_obj.get("imageUrl"),
                )
                equipped.append(ei)
                if ei.mintable:
                    mintable_count += 1

        # Arcane Symbols
        symbols = wearing.get("arcaneSymbols", char.get("arcaneSymbols", {}))
        for slot_data in symbols.get("slots", []):
            if not slot_data.get("itemId"):
                continue
            equipped.append(EquippedItem(
                slot="ARCANE",
                item_type="arcaneSymbol",
                item_id=slot_data.get("itemId", 0),
                level=slot_data.get("level", 0),
                exp=slot_data.get("currentExp", 0),
                max_exp=slot_data.get("totalExp", 0),
                force=slot_data.get("arcaneForce", 0),
                image_url=slot_data.get("imageUrl"),
            ))

        # Parse AP stats (camelCase keys in new API)
        ap_raw = char.get("apStat") or {}
        ap_stats = ApStats.from_api(ap_raw) if ap_raw else ApStats()

        # Parse Hyper Stats
        hyper_raw = char.get("hyperStat", {})
        hyper_stats = {
            k: v.get("level", 0)
            for k, v in hyper_raw.items()
            if isinstance(v, dict) and "level" in v
        }

        # Parse Ability Grades
        ability_block = char.get("ability", {})
        ability_grades = []
        for k in ["ability1", "ability2", "ability3"]:
            g = ability_block.get(k, {}).get("grade", 0) or 0
            ability_grades.append(g)

        return CharacterListing(
            token_id=str(data.get("tokenId", "") or data.get("assetKey", "")),
            name=data.get("name") or data.get("characterName") or common.get("nickname") or common.get("name") or "",
            class_name=job.get("className", ""),
            job_name=job.get("jobName", ""),
            class_code=job.get("classCode", 0),
            job_code=job.get("jobCode", 0),
            level=common.get("level", 0),
            price_wei=str(sales.get("priceWei", "0")),
            created_at=sales.get("createdAt"),
            nesolet_wei=str(common.get("nesoletWei") or common.get("nesolet") or "0"),
            ap_stats=ap_stats,
            asset_key=data.get("assetKey"),
            image_url=data.get("imageUrl"),
            equipped_items=equipped,
            mintable_count=mintable_count,
            hyper_stats=hyper_stats,
            ability_grades=ability_grades,
        )

    @staticmethod
    def from_navigator_api(info: dict, equip: dict, rich_items: dict = None) -> "CharacterListing":
        """Parse from Navigator /info, /equip-preset and rich item details mapping."""
        # info has the same base structure as Marketplace character
        char = CharacterListing.from_detail_api(info)
        
        preset_data = equip.get("preset", {})
        selected_idx = min(preset_data.get("selectedPreset", 0), 2)
        preset_key = f"preset{selected_idx + 1}"
        wearing = preset_data.get(preset_key, {})
        
        if wearing:
            equipped = []
            
            # 1. Base Equipment from Preset
            for slot_name, slot_data in wearing.items():
                if not isinstance(slot_data, dict) or not slot_data:
                    continue
                
                # The basic info from preset
                base_item = slot_data.get("item") or slot_data.get("data") or slot_data
                ak = base_item.get("assetKey") or slot_data.get("assetKey")
                
                # Use enriched rich info if available
                item_obj = rich_items.get(ak) if rich_items and ak else base_item
                if item_obj and "item" in item_obj: # if wrapped from items API
                    item_obj = item_obj["item"]

                ei = EquippedItem(
                    slot=slot_name,
                    item_type="equip",
                    item_id=item_obj.get("itemId", 0),
                    name=CharacterListing._get_name(item_obj),
                    token_id=ak or item_obj.get("tokenId"),
                    mintable=item_obj.get("isMinted", True),
                    potential_grade=CharacterListing._find_grade(item_obj),
                    starforce=item_obj.get("starforce", 0) or item_obj.get("starForce", 0) or CharacterListing._get_sf_deep(item_obj),
                    potential=CharacterListing._parse_pot(item_obj.get("potential") or item_obj.get("enhance", {}).get("potential")),
                    bonus_potential=CharacterListing._parse_pot(item_obj.get("bonusPotential") or item_obj.get("enhance", {}).get("bonusPotential")),
                    stats=item_obj.get("stats") or item_obj or {},
                    image_url=item_obj.get("imageUrl"),
                )
                equipped.append(ei)

            # 2. Secondary categories from Info (Cash, Pet, Arcane)
            char_node = info.get("character", {})
            w = char_node.get("wearing", {})
            
            for cat_name, slots in w.items():
                if cat_name in ["cashEquip", "pet", "arcaneSymbols"]:
                    # Note: arcaneSymbols has a slightly different structure 'slots'
                    if cat_name == "arcaneSymbols":
                        for sym in slots.get("slots", []):
                            ei = EquippedItem(
                                slot="Arcane", item_type="arcaneSymbol",
                                item_id=sym.get("itemId", 0),
                                name=f"Arcane Symbol (Lv.{sym.get('level', 1)})",
                                starforce=sym.get("level", 0),
                                image_url=sym.get("imageUrl"),
                                level=sym.get("level", 0),
                                exp=sym.get("currentExp", 0),
                                max_exp=sym.get("totalExp", 0),
                                force=sym.get("arcaneForce", 0)
                            )
                            # Backend computed: stats can hold more details
                            ei.stats = sym.get("stat")
                            equipped.append(ei)
                        continue

                    # Cash and Pet
                    for slot_name, raw_item in slots.items():
                        if not isinstance(raw_item, dict): continue
                        ak = raw_item.get("assetKey")
                        item_obj = rich_items.get(ak) if rich_items and ak else raw_item
                        if item_obj and "item" in item_obj:
                            item_obj = item_obj["item"]
                        
                        # Get best possible name
                        it_name = CharacterListing._get_name(item_obj) or item_obj.get("name") or slot_name
                        pa = item_obj.get("petAttr", {})
                        if not pa and "item" in item_obj:
                             pa = item_obj.get("item", {}).get("petAttr", {})
                        
                        it_name = pa.get("petName") or CharacterListing._get_name(item_obj) or item_obj.get("name") or slot_name

                        # Extract REAL skills if available
                        pet_skills = pa.get("skillNodes") or pa.get("skills") or []
                        if isinstance(pet_skills, dict): # Sometimes it's a map of nodes
                             pet_skills = list(pet_skills.values())

                        ei = EquippedItem(
                            slot=slot_name,
                            item_type="cashEquip" if cat_name == "cashEquip" else "pet",
                            item_id=item_obj.get("itemId") or item_obj.get("item_id") or 0,
                            name=it_name,
                            token_id=ak or item_obj.get("tokenId"),
                            image_url=item_obj.get("imageUrl"),
                            potential=CharacterListing._parse_pot(item_obj.get("potential") or item_obj.get("enhance", {}).get("potential")),
                            # Store entire node if stats missing, ensuring attributes are available
                            stats=(item_obj.get("stats") or item_obj or {}),
                        )
                        # Add extra metadata
                        if ei.stats:
                            ei.stats["petSkills"] = pet_skills
                            ei.stats["petAttr"] = pa
                        equipped.append(ei)

            char.equipped_items = equipped
            
        # Ensure name and level if from detail_api failed
        if not char.name or char.name == "":
            char.name = info.get("characterName") or info.get("character", {}).get("characterName", "")

        # Ensure tokenId is set to assetKey if missing (common in Navigator/Open API)
        if not char.token_id or char.token_id == "" or char.token_id == "None":
            char.token_id = info.get("assetKey") or info.get("character", {}).get("assetKey", "")

        return char

    @staticmethod
    def from_openapi(raw_char: dict) -> "CharacterListing":
        """Parse from MSU Open API /v1rc1/characters/... all-in-one response.
        Reshapes the Open API format to match what from_detail_api expects."""
        common = raw_char.get("common", {})
        reshaped = {
            "tokenId": raw_char.get("tokenInfo", {}).get("tokenId", ""),
            "name": common.get("name", ""),
            "assetKey": raw_char.get("assetKey", ""),
            "imageUrl": raw_char.get("image", {}).get("imageUrl", ""),
            "character": {
                "common": common,
                "apStat": raw_char.get("apStat", {}),
                "wearing": raw_char.get("wearing", {}),
                "hyperStat": raw_char.get("hyperStat", {}),
                "arcaneSymbols": raw_char.get("wearing", {}).get("arcaneSymbols", {}),
            },
        }
        return CharacterListing.from_detail_api(reshaped)
