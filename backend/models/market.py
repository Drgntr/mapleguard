from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class AnomalyType(str, Enum):
    WASH_TRADE = "wash_trade"
    BOT_SNIPE = "bot_snipe"
    PRICE_MANIPULATION = "price_manipulation"
    SAME_BLOCK_SNIPE = "same_block_snipe"


class ScarcityScore(BaseModel):
    token_id: str
    name: str
    score: float  # 0-100
    rank: int = 0
    total_items: int = 0
    percentile: float = 0.0
    breakdown: dict = {}  # attribute -> rarity contribution
    fair_value_estimate: float = 0.0


class AnomalyAlert(BaseModel):
    id: str
    anomaly_type: AnomalyType
    severity: str  # low, medium, high, critical
    description: str
    involved_wallets: list[str] = []
    involved_tokens: list[str] = []
    transaction_hashes: list[str] = []
    detected_at: datetime
    block_number: Optional[int] = None
    metadata: dict = {}


class UnderpricedItem(BaseModel):
    token_id: str
    name: str
    current_price: float
    fair_value: float
    discount_pct: float
    scarcity_score: float
    listed_at: Optional[datetime] = None
    image_url: Optional[str] = None


class MarketOverview(BaseModel):
    total_listed_items: int = 0
    total_listed_characters: int = 0
    volume_24h: float = 0.0
    transactions_24h: int = 0
    avg_item_price: float = 0.0
    avg_character_price: float = 0.0
    anomalies_24h: int = 0
    top_traded_items: list[dict] = []
    updated_at: Optional[datetime] = None
