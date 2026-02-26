# Mempool Orchestrator

An event-driven data platform that ingests, processes, and optimizes Bitcoin mempool dynamics for automated treasury management.

## Tech Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.12+ (managed by `uv`) |
| **Event Broker** | Redpanda (Kafka-compatible) |
| **Database** | PostgreSQL 16 (async via SQLAlchemy 2.0 + asyncpg) |
| **Messaging** | aiokafka (async Kafka producer/consumer) |
| **Web API** | FastAPI (async, read-only from PostgreSQL) |
| **Frontend** | Next.js + shadcn/ui (React dashboard) |
| **Infrastructure** | Docker / OrbStack |
| **IDE** | Antigravity (Gemini 3) |

## Architecture

Event-Driven Architecture (EDA) with Clean Architecture layers:

```
mempool.space WS ──→ Ingestor ──→ Redpanda ──→ State Consumer ──→ PostgreSQL ──→ API ──→ Dashboard
                    (workers/)     (Kafka)      (workers/)         (infra/db)    (api/)   (Next.js)
```

| Layer | Component | Responsibility |
|---|---|---|
| **Domain** | `src/domain/schemas.py` | Pydantic V2 contracts (zero external deps) |
| **Infrastructure** | `src/infrastructure/database/` | SQLAlchemy 2.0 async engine + ORM models |
| **Infrastructure** | `src/infrastructure/messaging/` | aiokafka producer with lifecycle management |
| **Workers** | `src/workers/ingestor.py` | WebSocket → Kafka (Signal & Fetch pattern) |
| **Workers** | `src/workers/state_consumer.py` | Kafka → PostgreSQL (idempotent materialization) |
| **API** | `src/api/` | Read-only FastAPI endpoints |
| **Core** | `src/core/config.py` | Centralized config via `pydantic-settings` |

### Decision Rules (Deterministic)

The orchestrator supports two strategy modes:

**🐢 PATIENT** (default) — Treasury operations, saves ~27.7%:
```python
IF fee_premium_pct > 20%:
    action = WAIT         # Target: Historical Median Fee
ELSE:
    action = BROADCAST    # Target: Current Median Fee
```

**⚡ RELIABLE** — Time-sensitive operations, 94% hit rate:
```python
action = BROADCAST        # Always, with EMA-20 smoothed fee
```

## Quick Start

### Prerequisites
- **Python 3.12+** (managed via `uv`)
- **Docker** (via OrbStack recommended)
- **Just** (Command Runner)

### Configuration
Create a `.env` file in the project root:
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MEMPOOL_TOPIC=mempool-raw
MEMPOOL_WS_URL=wss://mempool.space/api/v1/ws
MEMPOOL_API_URL=https://mempool.space/api
POSTGRES_DSN=postgresql+asyncpg://mempool:mempool@localhost:5432/mempool
```

### Project Structure
```text
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI endpoints + queries
│   │   ├── core/             # Configuration (pydantic-settings)
│   │   ├── domain/           # Pydantic V2 schemas (pure contracts)
│   │   ├── infrastructure/
│   │   │   ├── database/     # SQLAlchemy async engine + ORM models
│   │   │   └── messaging/    # aiokafka producer
│   │   └── workers/          # Async workers (ingestor, state_consumer)
│   ├── scripts/              # Maintenance (backfill_blocks.py)
│   └── tests/
├── frontend/                 # Next.js + shadcn/ui dashboard
├── infra/                    # Docker Compose (Redpanda, PostgreSQL)
└── docs/                     # ADRs, architecture, roadmap
```

### Installation
```bash
# Sync all dependencies
just sync

# Or sync individually
cd backend && uv sync
```

### Commands
```bash
# 1. Start Infrastructure (Redpanda + PostgreSQL)
just infra-up

# 2. System Health Check
just check

# 3. Backfill last 144 blocks (~24h) from mempool.space
just backfill

# 4. Launch Ingestion Pipeline (WS → Kafka)
just radar

# 5. Launch State Consumer (Kafka → PostgreSQL)
just state-writer

# 6. Launch API Server (reads from PostgreSQL)
just api

# 7. Launch Next.js Dashboard
just dashboard

# 8. Stop Infrastructure
just infra-down
```

## Data Models (PostgreSQL)

**`blocks` table** (confirmed blocks)
| Column | Type | Description |
|---|---|---|
| `height` | INTEGER (PK) | Block height |
| `hash` | VARCHAR(64) | Block hash |
| `timestamp` | BIGINT | Unix timestamp |
| `tx_count` | INTEGER | Transaction count |
| `size` | INTEGER | Block size (bytes) |
| `median_fee` | FLOAT | Median fee rate (sat/vB) |
| `total_fees` | BIGINT | Total fees (satoshis) |

**`mempool_snapshots` table** (point-in-time mempool state)
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment |
| `captured_at` | TIMESTAMPTZ | Server timestamp |
| `tx_count` | INTEGER | Mempool transaction count |
| `total_bytes` | BIGINT | Total mempool size |
| `total_fee_sats` | BIGINT | Total fees (satoshis) |
| `median_fee` | FLOAT | Fee floor proxy |

**`advisories` table** (RBF/CPFP recommendations)
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment |
| `txid` | VARCHAR(64) | Transaction ID (indexed) |
| `action` | VARCHAR(16) | BUMP / WAIT / CONFIRMED |
| `current_fee_rate` | FLOAT | Current fee rate |
| `target_fee_rate` | FLOAT | Recommended fee rate |

> **Convention:** All monetary values stored as integers in **Satoshis** to prevent floating-point precision errors.

## Testing

```bash
# Run all tests
just test

# Run specific test suite
cd backend && uv run pytest tests/test_config.py -v
```

**Test Coverage:**
- `tests/test_config.py`: Environment variable validation (12 tests)
- `tests/test_schemas.py`: Pydantic V2 contract validation
- `tests/test_ingestor.py`: WebSocket routing logic
- `tests/test_kafka_producer.py`: Kafka wrapper behavior
- `tests/test_api.py`: REST API client (httpx + respx mocking)

## Documentation

- [Architecture Guide](docs/architecture.md) - System design and component breakdown
- [Decision Log](docs/decisions.md) - Architectural decisions and project journal
- [Strategy Roadmap](docs/strategy.md) - Product vision and phased roadmap

## Development Workflow

This project follows a "Just-driven" workflow. All commands are defined in the `Justfile`:

```bash
just --list  # Show all available commands
```

Key recipes:
- `just check` — System health verification
- `just test` — Run test suite
- `just radar` — Start WebSocket ingestor
- `just state-writer` — Start Kafka → PostgreSQL consumer
- `just backfill` — Populate last 24h of blocks
- `just api` — Start FastAPI server
- `just dashboard` — Launch Next.js UI