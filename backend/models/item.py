from pydantic import BaseModel, computed_field
from typing import Optional
from datetime import datetime


class PotentialOption(BaseModel):
    label: str = ""
    grade: int = 0


class ItemPotential(BaseModel):
    option1: PotentialOption = PotentialOption()
    option2: PotentialOption = PotentialOption()
    option3: PotentialOption = PotentialOption()


class ItemStats(BaseModel):
    pad: int = 0  # Physical Attack Damage
    mad: int = 0  # Magic Attack Damage
    damr: int = 0  # Damage %
    statr: int = 0  # All Stats %
    bdr: int = 0  # Boss Damage %


class ItemAttribute(BaseModel):
    key: str
    value: str | int | float
    display_name: str = ""


class ItemListing(BaseModel):
    token_id: str
    name: str
    category_no: int = 0
    category_label: str = ""
    item_id: int = 0
    potential_grade: int = 0
    bonus_potential_grade: int = 0
    starforce: int = 0
    enable_starforce: bool = False
    price_wei: str = "0"
    created_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    seller: Optional[str] = None
    buyer: Optional[str] = None
    image_url: Optional[str] = None
    stats: Optional[ItemStats] = None
    potential: Optional[ItemPotential] = None
    bonus_potential: Optional[ItemPotential] = None
    attributes: list[ItemAttribute] = []
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None

    @computed_field
    @property
    def price(self) -> float:
        try:
            return int(self.price_wei) / 1e18
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def from_explore_api(raw: dict) -> "ItemListing":
        """Parse from /marketplace/explore/items response."""
        data = raw.get("data", {})
        sales = raw.get("salesInfo", {})
        category = raw.get("category", {})
        return ItemListing(
            token_id=str(raw.get("tokenId", "")),
            name=raw.get("name", ""),
            category_no=category.get("categoryNo", 0),
            category_label=category.get("label", ""),
            item_id=data.get("itemId", 0),
            potential_grade=data.get("potentialGrade", 0),
            bonus_potential_grade=data.get("bonusPotentialGrade", 0),
            starforce=data.get("starforce", 0),
            enable_starforce=data.get("enableStarforce", False),
            price_wei=str(sales.get("priceWei", "0")),
            created_at=sales.get("createdAt"),
            expired_at=sales.get("expiredAt"),
            image_url=raw.get("imageUrl"),
        )

    @staticmethod
    def from_recent_api(raw: dict) -> "ItemListing":
        """Parse from /dashboard/recently-listed response (item type)."""
        item = raw.get("item", {})
        sales = raw.get("salesInfo", {})
        return ItemListing(
            token_id=str(raw.get("tokenId", "")),
            name=raw.get("name", item.get("name", "")),
            starforce=item.get("starforce", 0),
            potential_grade=item.get("potentialGrade", 0),
            bonus_potential_grade=item.get("bonusPotentialGrade", 0),
            price_wei=str(sales.get("priceWei", "0")),
            created_at=sales.get("createdAt"),
            image_url=raw.get("imageUrl"),
        )

    @staticmethod
    def from_detail_api(raw: dict) -> "ItemListing":
        """Parse from /marketplace/items/{tokenId} detail response."""
        item = raw.get("item", {})
        sales = raw.get("salesInfo", {})
        stats_raw = item.get("stats", {})
        enhance = item.get("enhance", {})

        def _safe_extra(stat_key: str) -> int:
            """Safely extract 'extra' from a stat dict, handling None/null values."""
            val = stats_raw.get(stat_key)
            if isinstance(val, dict):
                return val.get("extra", 0) or 0
            return 0

        stats = ItemStats(
            pad=_safe_extra("pad"),
            mad=_safe_extra("mad"),
            damr=_safe_extra("damr"),
            statr=_safe_extra("statr"),
            bdr=_safe_extra("bdr"),
        )

        def _parse_potential(pot_raw: dict) -> ItemPotential:
            return ItemPotential(
                option1=PotentialOption(
                    label=pot_raw.get("option1", {}).get("label") or pot_raw.get("option1", {}).get("optionName", ""),
                    grade=pot_raw.get("option1", {}).get("grade", 0),
                ),
                option2=PotentialOption(
                    label=pot_raw.get("option2", {}).get("label") or pot_raw.get("option2", {}).get("optionName", ""),
                    grade=pot_raw.get("option2", {}).get("grade", 0),
                ),
                option3=PotentialOption(
                    label=pot_raw.get("option3", {}).get("label") or pot_raw.get("option3", {}).get("optionName", ""),
                    grade=pot_raw.get("option3", {}).get("grade", 0),
                ),
            )

        return ItemListing(
            token_id=str(raw.get("tokenId", "")),
            name=raw.get("name", item.get("name", item.get("common", {}).get("name", ""))),
            item_id=item.get("common", {}).get("itemId", 0),
            starforce=enhance.get("starforce", {}).get("enhanced", 0),
            potential_grade=enhance.get("potential", {}).get("option1", {}).get("grade", 0),
            bonus_potential_grade=enhance.get("bonusPotential", {}).get("option1", {}).get("grade", 0),
            price_wei=str(sales.get("priceWei", "0")),
            created_at=sales.get("createdAt"),
            image_url=raw.get("imageUrl") or item.get("common", {}).get("imageUrl"),
            stats=stats,
            potential=_parse_potential(enhance.get("potential", {})),
            bonus_potential=_parse_potential(enhance.get("bonusPotential", {})),
        )


    @staticmethod
    def from_openapi(raw_item: dict) -> "ItemListing":
        """Parse from MSU Open API /v1rc1/items/{assetKey} all-in-one response.
        Reshapes the Open API format to match what from_detail_api expects."""
        common = raw_item.get("common", {})
        reshaped = {
            "tokenId": raw_item.get("tokenInfo", {}).get("tokenId", ""),
            "name": common.get("itemName", ""),
            "assetKey": raw_item.get("assetKey", ""),
            "imageUrl": raw_item.get("image", {}).get("iconImageUrl", ""),
            "item": {
                "common": {**common, "name": common.get("itemName", "")},
                "enhance": raw_item.get("enhance", {}),
                "stats": raw_item.get("stats", {}),
            },
        }
        return ItemListing.from_detail_api(reshaped)


class ConsumableListing(BaseModel):
    name: str
    item_id: int = 0
    item_category: int = 0
    price_wei: str = "0"
    volume: int = 0
    price_change: float = 0.0
    image_url: Optional[str] = None

    @computed_field
    @property
    def price(self) -> float:
        try:
            return int(self.price_wei) / 1e18
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def from_api(raw: dict) -> "ConsumableListing":
        return ConsumableListing(
            name=raw.get("name", ""),
            item_id=raw.get("itemId", 0),
            item_category=raw.get("itemCategory", 0),
            price_wei=str(raw.get("priceWei", "0")),
            volume=raw.get("volume", 0),
            price_change=raw.get("priceChange", 0.0),
            image_url=raw.get("imageUrl"),
        )


class TradeRecord(BaseModel):
    price_wei: str = "0"
    created_at: Optional[datetime] = None

    @computed_field
    @property
    def price(self) -> float:
        try:
            return int(self.price_wei) / 1e18
        except (ValueError, TypeError):
            return 0.0


class OHLCBar(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    item_name: str = ""
