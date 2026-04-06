# MapleGuard Leaderboard Backend - Implementation Plan

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Database Schema Changes](#2-database-schema-changes)
3. [Proxy Rotation Module](#3-proxy-rotation-module)
4. [Step 1: Database Models](#step-1-database-models)
5. [Step 2: Scan All Characters Script](#step-2-scan-all-characters-script)
6. [Step 3: Scan All Items Script](#step-3-scan-all-items-script)
7. [Step 4: Watch New Mints Script](#step-4-watch-new-mints-script)
8. [Step 5: Watch New Item Mints Script](#step-5-watch-new-item-mints-script)
9. [Step 6: Enrich Characters Script](#step-6-enrich-characters-script)
10. [Step 7: Enrich Items Script](#step-7-enrich-items-script)
11. [Step 8: Leaderboard DB Service](#step-8-leaderboard-db-service)
12. [Step 9: Route Updates](#step-9-route-updates)
13. [Step 10: Configuration / Config Additions](#step-10-configuration-additions)
14. [Execution Order & Dependencies](#14-execution-order--dependencies)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Blockchain Layer                     │
│  Routescan API (ERC-721 transfers)                    │
│  RPC (eth_getLogs for Transfer events)               │
└──────┬──────────────────────────────┬────────────────┘
       │                              │
  scan_all_characters.py      scan_all_items.py
  (batch, historical)          (batch, historical)
       │                              │
       └──────────┬───────────────────┘
                  │
            DB: NftMintLookup
      (token_id → nft_type → exists)
                  │
       ┌──────────┼───────────────────┐
       │                              │
enrich_characters.py            enrich_items.py
  (batch, MSU OpenAPI)          (batch, MSU OpenAPI)
       │                              │
       └──────────┬───────────────────┘
                  │
 ┌────────────────┼─────────────────────────────┐
 │      SQLite DB (full snapshot cache)          │
 │  ┌────────────┐  ┌──────────┐                │
 │  │CharacterS- │  │ ItemSn-  │  ← pre-enriched│
 │  │napshot     │  │apshot    │                 │
 │  └────────────┘  └──────────┘                │
 │  ┌────────────┐  ┌──────────┐                │
 │  │SyncState   │  │MintEvent │  ← tracking    │
 │  └────────────┘  └──────────┘                 │
 └───────────────────────────────────────────┼────┘
                                             │
                            leaderboard_db_service.py
                                (DB-only reads)
                                             │
                            routes/leaderboard.py (updated)
```

**Live monitor** (runs permanently as background process):
```
watch_new_mints.py / watch_new_items_mints.py
  → Polls Routescan/RPC every N seconds
  → Detects Transfer(from=0x0) events (mints)
  → Inserts MintEvent + NftMintLookup into DB
  → Optionally triggers immediate enrichment
```

---

## 2. Database Schema Changes

### File: `C:\Scripts\Maple\MapleGuard\backend\db\database.py`

#### New Model: `NftMintLookup`
Tracks all known minted token_ids. This is the "existence" table that scan scripts populate. Lightweight -- one row per token_id found on chain.

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | auto |
| `token_id` | String(64) | **UNIQUE INDEX**, the numeric token_id on chain |
| `nft_type` | String(16) | `"character"` or `"item"` |
| `first_seen_block` | Integer | block where first Transfer event was seen |
| `first_seen_at` | DateTime | server_default=func.now() |

Indexes:
- `ix_mint_lookup_type_token` on `(nft_type, token_id)`
- `ix_mint_lookup_token` on `token_id` (unique)

#### New Model: `CharacterSnapshot`
Full character detail from MSU Open API, the source of truth for leaderboard CP.

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | auto |
| `token_id` | String(64) | **UNIQUE INDEX** |
| `asset_key` | String(256) | nullable, from Open API |
| `name` | String(256) | default "" |
| `class_name` | String(64) | default "" |
| `job_name` | String(64) | default "" |
| `level` | Integer | default 0 |
| `combat_power` | Integer | **indexed**, default 0 -- real CP from apStat.combatPower.total |
| `ap_stats_json` | Text | nullable, full apStat block as JSON |
| `hyper_stats_json` | Text | nullable |
| `wearing_json` | Text | nullable, equipped item slots summary |
| `image_url` | String(512) | nullable |
| `last_synced` | DateTime | **indexed**, server_default=func.now(), onupdate=func.now() |

Indexes:
- `ix_char_snap_cp` on `combat_power`
- `ix_char_snap_class_cp` on `(class_name, combat_power)`
- `ix_char_snap_synced` on `last_synced`

#### New Model: `ItemSnapshot`
Full item detail from MSU Open API / marketplace detail API.

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | auto |
| `token_id` | String(64) | **UNIQUE INDEX** |
| `asset_key` | String(256) | nullable |
| `name` | String(256) | default "" |
| `category_no` | Integer | default 0 |
| `category_label` | String(128) | default "" |
| `starforce` | Integer | default 0 |
| `potential_grade` | Integer | default 0 |
| `bonus_potential_grade` | Integer | default 0 |
| `stats_json` | Text | nullable, full stats block |
| `attributes_json` | Text | nullable, item attributes |
| `image_url` | String(512) | nullable |
| `last_synced` | DateTime | **indexed**, server_default=func.now() |

Indexes:
- `ix_item_snap_sf` on `starforce`
- `ix_item_snap_pg` on `potential_grade`
- `ix_item_snap_synced` on `last_synced`

#### New Model: `SyncState`
Tracks progress of batch and enrichment scripts. Key-value store pattern.

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | auto |
| `sync_key` | String(64) | **UNIQUE**, e.g. "char_scan_last_block", "item_enrich_last_token_id" |
| `sync_value` | String(512) | JSON-friendly string value |
| `updated_at` | DateTime | server_default=func.now(), onupdate=func.now() |

Predefined sync keys:
- `"char_scan_last_block"` -- last Routescan block scanned
- `"char_scan_cursor"` -- Routescan pagination cursor
- `"char_enrich_last_token_id"` -- last enriched numeric token_id
- `"item_scan_last_block"` -- same for items
- `"item_scan_cursor"` -- same for items
- `"item_enrich_last_token_id"` -- same for items
- `"mint_watch_char_last_block"` -- live watcher checkpoint
- `"mint_watch_item_last_block"` -- live watcher checkpoint

#### New Model: `MintEvent`
Tracks new mint events in real-time for monitoring and alerting.

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | auto |
| `token_id` | String(64) | indexed |
| `nft_type` | String(16) | indexed, `"character"` or `"item"` |
| `minter` | String(42) | the `to` address of the 0x0 mint transfer |
| `tx_hash` | String(66) | nullable |
| `block_number` | Integer | indexed |
| `timestamp` | Integer | blockchain timestamp |
| `enriched` | Boolean | default False, set True when enrichment completes |
| `created_at` | DateTime | server_default=func.now() |

Indexes:
- `ix_mint_event_type_block` on `(nft_type, block_number)`
- `ix_mint_event_enriched` on `enriched`

---

## 3. Proxy Rotation Module

### File: `C:\Scripts\Maple\MapleGuard\backend\services\proxy_pool.py` (NEW)

```python
class ProxyPool:
    """
    Rotating proxy pool for MSU Open API enrichment scripts.

    Proxy source: env var PROXY_CONFIG_PATH pointing to a JSON file:
      {"proxies": ["http://user:pass@ip:port", ...]}

    Features:
      - Round-robin rotation
      - Per-proxy health tracking (consecutive failures)
      - Automatic failover and ban/unban
      - Rate limit (429) detection and backoff
    """
```

Key methods:
- `__init__(config_path: Optional[str] = None)` - loads proxies from config file, falls back to no-proxy if file missing
- `get_proxy()` -> Optional[str] - returns next healthy proxy in rotation
- `report_success(proxy: str)` - marks proxy as healthy
- `report_failure(proxy: str, status_code: Optional[int])` - increments failure counter, removes from rotation if too many failures
- `rotate()` - advances to next proxy
- `healthy_count()` - number of currently healthy proxies

Integration pattern:
```python
async def http_get_with_proxy(url: str, pool: ProxyPool, max_retries: int = 3) -> Optional[dict]:
    """GET with automatic proxy rotation and retry."""
```

---

## Step-by-Step Implementation

### Step 1: Database Models

**File:** `C:\Scripts\Maple\MapleGuard\backend\db\database.py`

Add 5 new models: `NftMintLookup`, `CharacterSnapshot`, `ItemSnapshot`, `SyncState`, `MintEvent`.

Place models before the `engine = ...` line. All indexes as documented above.

Add helper functions:
```python
async def upsert_sync_state(session: AsyncSession, key: str, value: str):
    """UPSERT into SyncState table."""

async def get_sync_state(session: AsyncSession, key: str) -> Optional[str]:
    """Get sync state value by key."""
```

**Testing:** run `python -c "from db.database import init_db; import asyncio; asyncio.run(init_db())"` to verify tables are created.

---

### Step 2: Scan All Characters Script

**File:** `C:\Scripts\Maple\MapleGuard\backend\scripts\scan_all_characters.py` (NEW)

**CLI args:**
- `--start-from BLOCK` - start scanning from specific block
- `--resume` - resume from last saved checkpoint in DB (SyncState "char_scan_last_block" / "char_scan_cursor")
- `--dry-run` - scan but don't write to DB

**Logic:**
1. Load checkpoint from `SyncState` (or start from block 1)
2. Connect to Routescan API: `https://api.routescan.io/v2/network/mainnet/evm/68414/erc721-transfers?tokenAddress=CHAR_NFT&limit=100`
3. Paginate using `link.next` cursor (same pattern as `snowtrace_deep_scanner.py`)
4. For each item: extract `tokenId`, `blockNumber`
5. UPSERT into `NftMintLookup(token_id, nft_type="character", first_seen_block)`
6. Every 50 pages, update `SyncState` with last block + cursor
7. Handle Ctrl+C gracefully (save checkpoint)
8. On complete: print summary (total token_ids found, DB insert count)

**Key function signatures:**
```python
async def scan_blockchain_characters(
    client: httpx.AsyncClient,
    start_block: int = 1,
    resume: bool = False,
    dry_run: bool = False,
) -> int:
    """Scan all character minted token_ids from blockchain. Returns count found."""

async def _process_erc721_page(client, url, session) -> tuple[int, str|None]:
    """Fetch one page of ERC-721 transfers. Returns (inserted_count, next_cursor)."""
```

**Reused patterns:**
- Routescan base URL from `snowtrace_deep_scanner.py`: `https://api.routescan.io/v2/network/mainnet/evm/68414`
- Pagination via `data["link"]["next"]` cursor
- Checkpoint/resume state management
- Signal handler for Ctrl+C

---

### Step 3: Scan All Items Script

**File:** `C:\Scripts\Maple\MapleGuard\backend\scripts\scan_all_items.py` (NEW)

**Identical structure** to Step 2 but:
- Uses `ITEM_NFT` contract address instead of `CHAR_NFT`
- NFT type = `"item"`
- Sync keys = `"item_scan_last_block"`, `"item_scan_cursor"`

**Code reuse:** Consider a shared `_scan_nft_transfers()` helper in a new `scripts/_scan_helpers.py` module that both scripts call with different contract addresses.

---

### Step 4: Watch New Mints Script (Characters)

**File:** `C:\Scripts\Maple\MapleGuard\backend\scripts\watch_new_mints.py` (NEW)

**Purpose:** Runs as a long-lived background process. Polls for new character mints in real-time.

**Logic:**
1. Load last watched block from `SyncState` `"mint_watch_char_last_block"`
2. Every `POLL_INTERVAL` seconds (default 10):
   - Get current chain head via RPC `eth_blockNumber`
   - Query Routescan for ERC-721 transfers from last watched block to current
   - Filter for transfers where `from == 0x0000...0000` (mint)
   - For each new mint:
     - INSERT `NftMintLookup` (ON CONFLICT DO NOTHING)
     - INSERT `MintEvent` record
3. Update `SyncState` with last processed block
4. On Ctrl+C, save final state and exit cleanly

**CLI args:**
- `--poll-interval SECONDS` (default 10)
- `--start-block BLOCK` - override the last checkpoint

**Key function signatures:**
```python
async def watch_character_mints(
    poll_interval: int = 10,
    start_block: int = 0,
):
    """Infinite loop watching for new character mints."""

async def _detect_new_mints(client, from_block: int, to_block: int, session) -> list[dict]:
    """Fetch and process new character mints in block range."""
```

---

### Step 5: Watch New Item Mints Script

**File:** `C:\Scripts\Maple\MapleGuard\backend\scripts\watch_new_items_mints.py` (NEW)

**Identical structure** to Step 4 but for ITEM_NFT contract.

Sync key: `"mint_watch_item_last_block"`

---

### Step 6: Enrich Characters Script

**File:** `C:\Scripts\Maple\MapleGuard\backend\scripts\enrich_characters.py` (NEW)

**CLI args:**
- `--start-from TOKEN_ID` - start enrichment from specific numeric token_id
- `--resume` - resume from last checkpoint in DB
- `--batch-size N` (default 50) - number of characters to fetch per batch
- `--concurrency N` (default 3) - concurrent enrichment tasks
- `--stale-hours H` - re-enrich characters last synced more than H hours ago
- `--dry-run`

**Logic:**
1. Query `NftMintLookup` for characters not in `CharacterSnapshot` (or stale)
2. Build a list of `token_id` to enrich
3. For each token_id:
   a. Call MSU Open API `/characters/by-token-id/{token_id}` (see `openapi_service.py` and `market_data.py` `_get_openapi` pattern)
   b. Parse response using `CharacterListing.from_openapi()` from `models/character.py`
   c. Extract `combat_power` from `apStat.combatPower.total`
   d. INSERT/UPDATE `CharacterSnapshot` with parsed data
   e. Update `MintEvent.enriched = True` for this token_id
   f. Update `SyncState` `"char_enrich_last_token_id"`
4. Rate limiting:
   - Use token bucket (same as `openapi_service.py` -- 10 req/s)
   - Handle 429 responses: backoff 5s, rotate proxy, retry
5. Proxy rotation for all MSU Open API calls
6. Every 100 completions, print progress and flush to DB
7. On Ctrl+C: save checkpoint

**Key function signatures:**
```python
async def enrich_all_characters(
    start_from: int = 0,
    batch_size: int = 50,
    concurrency: int = 3,
    stale_hours: int = 0,
    dry_run: bool = False,
):
    """Batch-enrich character snapshots from MSU Open API."""

async def _enrich_single_character(
    client: httpx.AsyncClient,
    session: AsyncSession,
    token_id: str,
    proxy_pool: Optional[ProxyPool],
) -> dict | None:
    """Enrich one character. Returns snapshot data or None on failure."""

async def _fetch_openapi_with_retry(
    client, path: str, proxy_pool: Optional[ProxyPool], max_retries: int = 3,
) -> Optional[dict]:
    """GET from Open API with proxy rotation and 429 backoff."""
```

**Data flow:**
```
NftMintLookup(token_id="12345", nft_type="character")
  → GET https://openapi.msu.io/v1rc1/characters/by-token-id/12345
  → Parse with CharacterListing.from_openapi()
  → CharacterSnapshot(
      token_id="12345",
      asset_key=char.asset_key,
      name=char.name,
      class_name=char.class_name,
      level=char.level,
      combat_power=char.ap_stats.combat_power.total,
      ap_stats_json=json.dumps(ap_stats_raw),
      hyper_stats_json=json.dumps(char.hyper_stats),
      wearing_json=json.dumps(equipped_summary),
      image_url=char.image_url,
    )
  → MintEvent.enriched = True
```

---

### Step 7: Enrich Items Script

**File:** `C:\Scripts\Maple\MapleGuard\backend\scripts\enrich_items.py` (NEW)

**Identical structure** to Step 6 but:
- Queries `NftMintLookup` for items
- Calls MSU Open API `/items/{asset_key}` (for ITEM-prefixed IDs) or marketplace detail API for numeric IDs
- Uses `ItemListing.from_openapi()` and `ItemListing.from_detail_api()` parsers from `models/item.py`
- Inserts into `ItemSnapshot`

**Key differences from character enrichment:**
1. Item enrichment can use two API paths:
   - **Open API path** (preferred): `/items/{asset_key}` where asset_key starts with "ITEM"
   - **Marketplace detail path**: `/marketplace/items/{token_id}` to discover asset_key, then call Open API
2. Numeric token_ids need a marketplace lookup first to get the asset_key
3. Stats are stored in `stats_json` and `attributes_json` columns

**Key function signatures:**
```python
async def enrich_all_items(
    start_from: int = 0,
    batch_size: int = 50,
    concurrency: int = 3,
    stale_hours: int = 0,
    dry_run: bool = False,
):
    """Batch-enrich item snapshots from MSU APIs."""
```

---

### Step 8: Leaderboard DB Service

**File:** `C:\Scripts\Maple\MapleGuard\backend\services\leaderboard_db_service.py` (NEW)

This is the core new service. All reads from SQLite only, zero API calls.

```python
class LeaderboardDBService:
    """
    Database-backed leaderboard service.
    All queries read from SQLite (CharacterSnapshot, ItemSnapshot, NftMintLookup,
    MintEvent, SyncState). No live API calls.
    """
```

**Methods:**

```python
async def get_cp_leaderboard(
    class_name: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """
    Top characters by combat_power from CharacterSnapshot.
    If class_name given, filters to that class.
    Returns:
    {
        "characters": [{"token_id", "name", "class_name", "level", "combat_power", "image_url"}],
        "total_count": int,
        "class_name": str or None,
    }
    """
    # SQL: SELECT FROM character_snapshots WHERE class_name = :cls
    #      ORDER BY combat_power DESC LIMIT :limit OFFSET :offset
```

```python
async def get_combined_leaderboard(
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """
    Top characters by combat_power across all classes, grouped by class.
    Returns:
    {
        "characters": [...],  # flat list top N by CP
        "by_class": {         # grouped by class
            "Shadower": [...],
            "Hero": [...],
        },
        "total_enriched": int,
    }
    ```

```python
async def get_char_detail(token_id: str) -> dict | None:
    """
    Get full character detail from CharacterSnapshot.
    Returns parsed snapshot with ap_stats, hyper_stats, wearing deserialized from JSON.
    """
```

```python
async def get_item_detail(token_id: str) -> dict | None:
    """Get full item detail from ItemSnapshot."""
```

```python
async def get_recent_mints(
    nft_type: str = "character",
    limit: int = 50,
) -> list[dict]:
    """
    Get recently minted NFTs from MintEvent table.
    Returns: [{"token_id", "nft_type", "minter", "block_number", "timestamp", "enriched"}]
    """
```

```python
async def get_stats() -> dict:
    """
    Dashboard stats:
    {
        "total_characters_minted": int,           -- COUNT(NftMintLookup WHERE nft_type='character')
        "total_items_minted": int,                -- COUNT(NftMintLookup WHERE nft_type='item')
        "total_characters_enriched": int,         -- COUNT(CharacterSnapshot)
        "total_items_enriched": int,              -- COUNT(ItemSnapshot)
        "char_scan_last_block": int,
        "item_scan_last_block": int,
        "last_char_enriched_token_id": str,
        "last_item_enriched_token_id": str,
        "recent_mints_24h": int,                  -- COUNT(MintEvent WHERE timestamp > now-24h)
        "mints_pending_enrichment": int,           -- COUNT(MintEvent WHERE enriched=False)
    }
    """
```

```python
async def batch_upsert_characters(characters: list[dict]):
    """Bulk upsert into CharacterSnapshot. Used by enrichment scripts."""

async def batch_upsert_items(items: list[dict]):
    """Bulk upsert into ItemSnapshot."""
```

```python
async def get_classes_list() -> list[str]:
    """Get list of distinct class_name values with counts."""
```

```python
async def search_characters(
    keyword: str,
    class_name: str | None = None,
    level_min: int = 0,
    level_max: int = 300,
    limit: int = 50,
) -> list[dict]:
    """Search characters by name/keyword with filters."""
```

**Singleton:**
```python
leaderboard_db_service = LeaderboardDBService()
```

---

### Step 9: Route Updates

**File:** `C:\Scripts\Maple\MapleGuard\backend\routes\leaderboard.py`

**Changes:**
1. Import `leaderboard_db_service` from `services.leaderboard_db_service`
2. Update `/api/leaderboard/scan` endpoint:
   - **Primary path**: Read from `leaderboard_db_service.get_cp_leaderboard()`
   - **Fallback**: If DB is empty (< 10 records), fall back to existing `leaderboard_service` (current API-based logic)
   - Keep cache layer for frequent requests
3. Update `/api/leaderboard/combined` endpoint:
   - Use `leaderboard_db_service.get_combined_leaderboard()` (instant DB query)
4. **New endpoints**:
   - `GET /api/leaderboard/stats` -> `leaderboard_db_service.get_stats()`
   - `GET /api/leaderboard/characters/{token_id}` -> `leaderboard_db_service.get_char_detail(token_id)`
   - `GET /api/leaderboard/items/{token_id}` -> `leaderboard_db_service.get_item_detail(token_id)`
   - `GET /api/leaderboard/recent-mints` -> `leaderboard_db_service.get_recent_mints()`
   - `GET /api/leaderboard/classes` -> `leaderboard_db_service.get_classes_list()`
   - `GET /api/leaderboard/characters/search?q=KEYWORD` -> `leaderboard_db_service.search_characters()`

**Updated endpoint structure:**

```python
@router.get("/scan")
async def leaderboard_scan(limit: int = Query(50, ge=1, le=200)):
    # 1. Try DB-backed service (instant)
    result = await leaderboard_db_service.get_combined_leaderboard(limit=limit)
    if result["total_enriched"] > 0:
        return result
    # 2. Fallback to live API scan (existing behavior)
    return await _fallback_live_scan(limit)

@router.get("/stats")
async def leaderboard_stats():
    return await leaderboard_db_service.get_stats()

@router.get("/characters/{token_id}")
async def character_detail(token_id: str):
    detail = await leaderboard_db_service.get_char_detail(token_id)
    if detail:
        return detail
    # 3. Fallback to live API
    return await market_data_service.fetch_character_detail(token_id)

@router.get("/recent-mints")
async def recent_mints(
    nft_type: str = Query("character"),
    limit: int = Query(50, ge=1, le=200),
):
    return await leaderboard_db_service.get_recent_mints(nft_type, limit)

@router.get("/classes")
async def list_classes():
    return await leaderboard_db_service.get_classes_list()
```

**Backward compatibility:** All existing endpoints keep their exact response shapes. New endpoints just add more data. The fallback ensures nothing breaks if the DB is not yet populated.

---

### Step 10: Configuration Additions

**File:** `C:\Scripts\Maple\MapleGuard\backend\config.py`

Add to `Settings` class:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Leaderboard Enrichment
    PROXY_CONFIG_PATH: str = ""                          # path to proxy config JSON
    ENRICH_CONCURRENCY: int = 3                           # default enrichment concurrency
    ENRICH_STALE_HOURS: int = 24                          # re-enrich after this many hours
    ENRICH_RATE_LIMIT_RPS: float = 8.0                    # requests per second (below API limit of 10)
    ENRICH_RETRY_MAX: int = 5                             # max retries per request

    # Routescan
    ROUTESCAN_BASE: str = "https://api.routescan.io/v2/network/mainnet/evm/68414"

    # Mint Watcher
    MINT_WATCH_POLL_INTERVAL: int = 10                    # seconds between polls
    MINT_WATCH_BATCH_SIZE: int = 100                      # max mints per poll cycle
```

---

## 14. Execution Order & Dependencies

### Phase 1: Infrastructure (Day 1)
1. Add new DB models to `db/database.py` and run migration
2. Create `services/proxy_pool.py`
3. Create `services/leaderboard_db_service.py` (methods first, empty DB is fine)
4. Add config additions to `config.py`
5. Add route updates to `routes/leaderboard.py` (with fallbacks)

### Phase 2: Historical Scan (Day 2)
6. Run `scripts/scan_all_characters.py` - populates `NftMintLookup` with all character token_ids
7. Run `scripts/scan_all_items.py` - populates `NftMintLookup` with all item token_ids

### Phase 3: Enrichment (Day 3-5, depends on API quotas)
8. Run `scripts/enrich_characters.py` - populates `CharacterSnapshot` (runs in background, checkpoint-resumable)
9. Run `scripts/enrich_items.py` - populates `ItemSnapshot` (runs in background)

### Phase 4: Live Monitoring (ongoing)
10. Deploy `scripts/watch_new_mints.py` as background service
11. Deploy `scripts/watch_new_items_mints.py` as background service

### Phase 5: Production
12. Leaderboard endpoints now serve from DB (instant)
13. New mints are detected in real-time and queued for enrichment
14. Periodic re-enrichment cron for stale records

## File Summary

| # | File Path | Action |
|---|-----------|--------|
| 1 | `C:\Scripts\Maple\MapleGuard\backend\db\database.py` | **Edit** - Add 5 new models: NftMintLookup, CharacterSnapshot, ItemSnapshot, SyncState, MintEvent |
| 2 | `C:\Scripts\Maple\MapleGuard\backend\config.py` | **Edit** - Add enrichment/watcher config fields |
| 3 | `C:\Scripts\Maple\MapleGuard\backend\services\proxy_pool.py` | **New** - Proxy rotation with health checks |
| 4 | `C:\Scripts\Maple\MapleGuard\backend\services\leaderboard_db_service.py` | **New** - DB-only leaderboard queries |
| 5 | `C:\Scripts\Maple\MapleGuard\backend\scripts\scan_all_characters.py` | **New** - Blockchain scan for all character token_ids |
| 6 | `C:\Scripts\Maple\MapleGuard\backend\scripts\scan_all_items.py` | **New** - Blockchain scan for all item token_ids |
| 7 | `C:\Scripts\Maple\MapleGuard\backend\scripts\watch_new_mints.py` | **New** - Live character mint watcher |
| 8 | `C:\Scripts\Maple\MapleGuard\backend\scripts\watch_new_items_mints.py` | **New** - Live item mint watcher |
| 9 | `C:\Scripts\Maple\MapleGuard\backend\scripts\enrich_characters.py` | **New** - OpenAPI enrichment for characters |
| 10 | `C:\Scripts\Maple\MapleGuard\backend\scripts\enrich_items.py` | **New** - OpenAPI enrichment for items |
| 11 | `C:\Scripts\Maple\MapleGuard\backend\routes\leaderboard.py` | **Edit** - Use DB service, add new endpoints |
| 12 | `C:\Scripts\Maple\MapleGuard\backend\scripts\_scan_helpers.py` | **New (optional)** - Shared scan utilities |
