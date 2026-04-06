from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Resolve .env from project root (one level above backend/)
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # MSU / Nexpace API
    MSU_API_BASE: str = "https://msu.io/marketplace/api"
    MSU_GATEWAY_BASE: str = "https://msu.io/marketplace/api/gateway/v1"
    MSU_NAVIGATOR_BASE: str = "https://msu.io/navigator/api/navigator"

    # MSU Open API (Official Builder API v1rc1)
    MSU_OPENAPI_BASE: str = "https://openapi.msu.io/v1rc1"
    MSU_OPENAPI_KEY: str = ""

    # Henesys Chain
    CHAIN_ID: int = 68414
    RPC_URL: str = "https://henesys-rpc.msu.io"

    # Smart Contracts
    MARKETPLACE_CONTRACT: str = "0x6813869c3e5dec06e6f88b42d41487dc5d7abf57"
    SIGNING_CONTRACT: str = "0xf1c82c082af3de3614771105f01dc419c3163352"
    PAYMENT_TOKEN: str = "0x07E49Ad54FcD23F6e7B911C2068F0148d1827c08"
    CHARACTER_NFT: str = "0xcE8e48Fae05c093a4A1a1F569BDB53313D765937"
    ITEM_NFT: str = "0x43DCff2A0cedcd5e10e6f1c18b503498dDCe60d5"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 30
    CACHE_TTL_LONG: int = 300

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./mapleguard.db"

    # Indexer
    INDEXER_START_BLOCK: int = 0
    INDEXER_POLL_INTERVAL: int = 2

    # Anomaly Detection
    WASH_TRADE_WINDOW_SECONDS: int = 3600
    WASH_TRADE_MIN_TXNS: int = 3
    SNIPE_BLOCK_THRESHOLD: int = 1

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
