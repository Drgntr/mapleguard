from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Text, Index, func
from datetime import datetime
from typing import Optional

from config import get_settings


class Base(DeclarativeBase):
    pass


class ItemListingDB(Base):
    __tablename__ = "item_listings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(256))
    category_no: Mapped[int] = mapped_column(Integer, default=0)
    item_id: Mapped[int] = mapped_column(Integer, default=0)
    potential_grade: Mapped[int] = mapped_column(Integer, default=0)
    bonus_potential_grade: Mapped[int] = mapped_column(Integer, default=0)
    starforce: Mapped[int] = mapped_column(Integer, default=0)
    price_wei: Mapped[str] = mapped_column(String(78), default="0")
    price_converted: Mapped[float] = mapped_column(Float, default=0.0)
    seller: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)
    buyer: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    block_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attributes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    listed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_item_name", "name"),
        Index("ix_item_category", "category_no"),
        Index("ix_item_price", "price_converted"),
        Index("ix_item_block", "block_number"),
        Index("ix_item_seller", "seller"),
        Index("ix_item_buyer", "buyer"),
    )


class CharacterListingDB(Base):
    __tablename__ = "character_listings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(256))
    class_name: Mapped[str] = mapped_column(String(64), default="")
    job_name: Mapped[str] = mapped_column(String(64), default="")
    level: Mapped[int] = mapped_column(Integer, default=0)
    price_wei: Mapped[str] = mapped_column(String(78), default="0")
    price_converted: Mapped[float] = mapped_column(Float, default=0.0)
    seller: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)
    buyer: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    block_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nesolet_wei: Mapped[Optional[str]] = mapped_column(String(78), nullable=True)
    ap_stats_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    asset_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    listed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_char_class", "class_name"),
        Index("ix_char_level", "level"),
        Index("ix_char_price", "price_converted"),
        Index("ix_char_seller", "seller"),
    )


class CharacterCP(Base):
    __tablename__ = "character_cp"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    asset_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    name: Mapped[str] = mapped_column(String(256), default="")
    class_name: Mapped[str] = mapped_column(String(64), default="")
    level: Mapped[int] = mapped_column(Integer, default=0)
    combat_power: Mapped[int] = mapped_column(Integer, default=0)
    # Raw apStat snapshot for re-calculation
    ap_stats_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Source: "openapi" (real), "derived" (estimated from stats)
    source: Mapped[str] = mapped_column(String(16), default="openapi")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_char_cp_value", "combat_power"),
        Index("ix_char_cp_class", "class_name", "combat_power"),
    )


class AnomalyDB(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anomaly_type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(Text)
    involved_wallets_json: Mapped[str] = mapped_column(Text, default="[]")
    involved_tokens_json: Mapped[str] = mapped_column(Text, default="[]")
    tx_hashes_json: Mapped[str] = mapped_column(Text, default="[]")
    block_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OrderMatchDB(Base):
    __tablename__ = "order_matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tx_hash: Mapped[str] = mapped_column(String(66))
    block_number: Mapped[int] = mapped_column(Integer)
    log_index: Mapped[int] = mapped_column(Integer)
    order_hash: Mapped[str] = mapped_column(String(66))
    maker: Mapped[str] = mapped_column(String(42))
    taker: Mapped[str] = mapped_column(String(42))
    token_id: Mapped[str] = mapped_column(String(128))
    nft_address: Mapped[str] = mapped_column(String(42))
    payment_token: Mapped[str] = mapped_column(String(42))
    price_wei: Mapped[str] = mapped_column(String(78))
    listing_time: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NFTTransferDB(Base):
    __tablename__ = "nft_transfers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tx_hash: Mapped[str] = mapped_column(String(66))
    block_number: Mapped[int] = mapped_column(Integer)
    log_index: Mapped[int] = mapped_column(Integer)
    contract_address: Mapped[str] = mapped_column(String(42))
    from_address: Mapped[str] = mapped_column(String(42))
    to_address: Mapped[str] = mapped_column(String(42))
    token_id: Mapped[str] = mapped_column(String(128))
    nft_type: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


engine = create_async_engine(get_settings().DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class NftMintLookup(Base):
    """Lightweight existence table for all minted NFT token IDs."""
    __tablename__ = "nft_mint_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    nft_type: Mapped[str] = mapped_column(String(16))  # "character" or "item"
    minter: Mapped[str] = mapped_column(String(42), default="")
    block_number: Mapped[int] = mapped_column(Integer, default=0)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_nft_token_type", "nft_type", "token_id"),
    )


class CharacterSnapshot(Base):
    """Full character detail snapshot with pre-computed CP."""
    __tablename__ = "character_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    asset_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    name: Mapped[str] = mapped_column(String(256), default="")
    class_name: Mapped[str] = mapped_column(String(64), default="")
    job_name: Mapped[str] = mapped_column(String(64), default="")
    class_code: Mapped[int] = mapped_column(Integer, default=0)
    job_code: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=0)
    combat_power: Mapped[int] = mapped_column(Integer, default=0)
    char_att: Mapped[float] = mapped_column(Float, default=0.0)
    char_matt: Mapped[float] = mapped_column(Float, default=0.0)
    ap_stats_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hyper_stats_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    wearing_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    equipped_items_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    price_wei: Mapped[str] = mapped_column(String(78), default="0")
    source: Mapped[str] = mapped_column(String(16), default="openapi")
    last_synced: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_char_snap_cp", "combat_power"),
        Index("ix_char_snap_class", "class_name", "combat_power"),
        Index("ix_char_snap_level", "level"),
        Index("ix_char_snap_name", "name"),
    )


class ItemSnapshot(Base):
    """Full item detail snapshot."""
    __tablename__ = "item_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    asset_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    name: Mapped[str] = mapped_column(String(256), default="")
    category_no: Mapped[int] = mapped_column(Integer, default=0)
    category_label: Mapped[str] = mapped_column(String(128), default="")
    item_id: Mapped[int] = mapped_column(Integer, default=0)
    starforce: Mapped[int] = mapped_column(Integer, default=0)
    enable_starforce: Mapped[bool] = mapped_column(default=False)
    potential_grade: Mapped[int] = mapped_column(Integer, default=0)
    bonus_potential_grade: Mapped[int] = mapped_column(Integer, default=0)
    stats_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    potential_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bonus_potential_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attributes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    price_wei: Mapped[str] = mapped_column(String(78), default="0")
    source: Mapped[str] = mapped_column(String(16), default="openapi")
    last_synced: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_item_snap_cat", "category_no"),
        Index("ix_item_snap_sf", "starforce"),
        Index("ix_item_snap_pg", "potential_grade"),
        Index("ix_item_snap_name", "name"),
    )


class SyncState(Base):
    """Key-value checkpoint store for scan/enrich state."""
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class MintEvent(Base):
    """Real-time mint event tracking."""
    __tablename__ = "mint_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(String(128), index=True)
    nft_type: Mapped[str] = mapped_column(String(16))  # "character" or "item"
    minter: Mapped[str] = mapped_column(String(42), default="")
    block_number: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[int] = mapped_column(Integer, default=0)
    enriched: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_mint_type_block", "nft_type", "block_number"),
        Index("ix_mint_enriched", "enriched", "nft_type"),
    )


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
