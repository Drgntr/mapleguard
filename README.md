# MapleGuard & Market Sentinel

Real-time market intelligence platform for **MapleStory Universe** (MSU) on the Henesys blockchain. A Bloomberg-style terminal for NFT marketplace analytics, scarcity scoring, and anomaly detection.

## Architecture

```
MapleGuard/
├── backend/          # FastAPI - REST API, Rarity Engine, Anomaly Detection
├── indexer/          # Node.js/Ethers.js - Blockchain event indexer
├── frontend/         # Next.js + Tailwind CSS - Terminal-style dashboard
├── docker-compose.yml
└── .env.example
```

### Components

| Component | Stack | Purpose |
|-----------|-------|---------|
| **Backend API** | FastAPI + SQLAlchemy + Redis | Market data API, scarcity scoring, anomaly detection |
| **Blockchain Indexer** | Node.js + Ethers.js + better-sqlite3 | Monitors Transfer & OrderMatched events on Henesys |
| **Frontend** | Next.js 15 + Tailwind CSS + lightweight-charts | Bloomberg/terminal dark mode dashboard |
| **Cache** | Redis | Reduces RPC and API calls with configurable TTL |

## Quick Start

### Prerequisites

- Node.js >= 20
- Python >= 3.12
- Redis (or Docker)

### 1. Environment Setup

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start with Docker (recommended)

```bash
docker compose up -d
```

This starts Redis, the backend API (port 8000), the indexer, and the frontend (port 3000).

### 3. Manual Setup

**Redis:**
```bash
# Start Redis locally or via Docker
docker run -d --name mapleguard-redis -p 6379:6379 redis:7-alpine
```

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Indexer:**
```bash
cd indexer
npm install
npm run dev
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## API Endpoints

### Items
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/items/` | List items with pagination |
| GET | `/api/items/recently-listed` | Recently listed items/characters |
| GET | `/api/items/{token_id}/scarcity` | Scarcity score for a specific item |
| GET | `/api/items/underpriced` | Items below fair market value |
| GET | `/api/items/{item_name}/ohlc` | OHLC candlestick price data |

### Characters
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/characters/` | List characters with filtering |
| GET | `/api/characters/floor-prices` | Floor prices by class/level bracket |

### Market Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/market/overview` | High-level market statistics |
| GET | `/api/market/anomalies` | Detected wash trades, bot snipes |
| GET | `/api/market/scarcity-ranking` | Items ranked by scarcity score |

## MSU/Nexpace API Configuration

The platform connects to the MapleStory Universe marketplace API:

| Setting | Default | Description |
|---------|---------|-------------|
| `MSU_API_BASE` | `https://msu.io/marketplace/api` | Main marketplace API |
| `MSU_GATEWAY_BASE` | `https://msu.io/marketplace/api/gateway/v1` | Gateway API (newer endpoints) |
| `RPC_URL` | `https://subnets.avax.network/maplestory/mainnet/rpc` | Henesys chain RPC |

### Henesys Chain Details

- **Chain ID:** 68414
- **Block time:** ~2 seconds
- **Marketplace listing delay:** 30 seconds (purchases only allowed 30s after listing)

### Smart Contracts (Henesys)

| Contract | Address | Purpose |
|----------|---------|---------|
| Marketplace | `0x6813869c3e5dec06e6f88b42d41487dc5d7abf57` | Order matching |
| Signing | `0xf1c82c082af3de3614771105f01dc419c3163352` | EIP-712 verification |
| NESOLET | `0x07E49Ad54FcD23F6e7B911C2068F0148d1827c08` | Payment token |
| Character NFT | `0xcE8e48Fae05c093a4A1a1F569BDB53313D765937` | ERC-721 characters |
| Item NFT | `0x43DCff2A0cedcd5e10e6f1c18b503498dDCe60d5` | ERC-721 items |

## Scarcity Score Algorithm

The rarity engine computes a 0-100 score using weighted attribute analysis:

| Component | Weight | Logic |
|-----------|--------|-------|
| Name rarity | 20% | `1 - (count_of_name / total_items)` |
| Attribute rarity | 40% | Average trait frequency across all attributes |
| Starforce bonus | 20% | Rarity of enhancement level with tier multipliers |
| Potential grade | 20% | Rarity of potential tier with grade multipliers |

**Fair value estimation:** median price of same-name items, adjusted by scarcity score.

## Anomaly Detection

### Wash Trading
Flags wallet pairs with >= 3 transactions within a 1-hour sliding window.

### Bot Sniping
Detects purchases that occur within 1 block of listing creation, bypassing the mandatory 30-second marketplace delay.

### Price Manipulation
Identifies when > 60% of recent trades for an item are concentrated in 2 wallets.

## Cache Strategy

Redis caching with two TTL tiers:
- **Short TTL (30s):** Live listings, recently listed, market overview
- **Long TTL (5min):** Scarcity scores, OHLC data, rankings

Cache keys follow the pattern `{resource}:{params}` and are automatically invalidated.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), Pydantic v2, Redis
- **Indexer:** Node.js 20, Ethers.js v6, better-sqlite3, ioredis
- **Frontend:** Next.js 15, React 19, Tailwind CSS 3, lightweight-charts (TradingView)
- **Infrastructure:** Docker Compose, Redis 7
