# Mempool Orchestrator

An event-driven data platform that ingests, processes, and visualizes Bitcoin mempool dynamics for fee optimization and treasury management.

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
| **Workers** | `src/workers/ingestor.py` | WebSocket → Kafka (Signal & Fetch pattern, ADR-021 fee enrichment) |
| **Workers** | `src/workers/state_consumer.py` | Kafka → PostgreSQL (idempotent materialization + Snapshot pattern) |
| **Workers** | `src/workers/backfill.py` | Incremental block gap detection + auto-fill on boot |
| **Workers** | `src/workers/tx_hunter.py` | Advisory engine: polls stuck TXs, calculates RBF/CPFP fees |
| **API** | `src/api/` | Read-only FastAPI endpoints |
| **Core** | `src/core/config.py` | Centralized config via `pydantic-settings` |

## Quick Start

### Prerequisites
- **Python 3.12+** (managed via `uv`)
- **Docker** (via OrbStack recommended)
- **Just** (Command Runner)

### Configuration
Copy `.env.example` to `.env` and adjust values:
```bash
cp .env.example .env
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
│   │   └── workers/          # Async workers (ingestor, state_consumer, backfill, tx_hunter)
│   ├── scripts/              # Maintenance (backfill, migrations)
│   └── tests/
├── frontend/                 # Next.js + shadcn/ui dashboard
├── infra/                    # Docker Compose (Redpanda, PostgreSQL, pgAdmin)
└── docs/                     # ADRs, architecture, roadmap
```

### Installation
```bash
just sync
```

### Commands
```bash
# Infrastructure
just infra-up         # Start Redpanda + PostgreSQL + pgAdmin
just infra-down       # Stop all services
just infra-status     # View running containers
just db-viewer        # Open pgAdmin in browser (port 5050)

# Data Pipeline
just backfill         # Incremental block backfill (gap detection)
just radar            # Launch Ingestor (WS → Kafka)
just state-writer     # Launch State Consumer (Kafka → PostgreSQL)
just hunter           # Launch Advisory Engine (RBF/CPFP scanner)

# API & Frontend
just api              # Start FastAPI server (port 8000, auto-backfills on boot)
just dashboard        # Launch Next.js dashboard (port 3000)

# Maintenance
just test             # Run backend test suite
just check            # System health check
just sync             # Sync backend dependencies
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
| `pool_name` | VARCHAR(64) | Mining pool name |
| `fee_range` | JSONB | Fee rate distribution array |

**`mempool_snapshots` table** (point-in-time mempool state)
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment |
| `captured_at` | TIMESTAMPTZ | Server timestamp |
| `tx_count` | INTEGER | Mempool transaction count |
| `total_bytes` | BIGINT | Total mempool size |
| `total_fee_sats` | BIGINT | Total fees (satoshis) |
| `median_fee` | FLOAT | Fee floor proxy |

**`mempool_block_projections` table** (projected blocks — Snapshot pattern)
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment |
| `captured_at` | TIMESTAMPTZ | Server timestamp |
| `block_index` | INTEGER | 0 = next block |
| `block_size` | INTEGER | Projected block size (bytes) |
| `block_v_size` | FLOAT | Virtual size |
| `n_tx` | INTEGER | Transaction count |
| `total_fees` | BIGINT | Total fees (satoshis) |
| `median_fee` | FLOAT | Median fee rate (sat/vB) |
| `fee_range` | JSONB | Fee rate distribution array |

> **Convention:** All monetary values stored as integers in **Satoshis** to prevent floating-point precision errors.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/mempool/stats` | Mempool KPIs: size, fees, blocks_to_clear, 1h deltas |
| `GET` | `/api/blocks/recent` | Confirmed blocks with pool_name and fee_range |
| `GET` | `/api/orchestrator/status` | Market analytics: EMA, trend, real-time confidence (dynamic) |
| `GET` | `/api/watchlist` | Tracked transactions with RBF/CPFP advisories |

## Testing

```bash
just test    # 78 tests
```

**Test Coverage:**
- `tests/test_config.py`: Environment variable validation (12 tests)
- `tests/test_schemas.py`: Pydantic V2 contract validation (13 tests)
- `tests/test_ingestor.py`: WebSocket routing + ADR-021 enrichment (11 tests)
- `tests/test_kafka_producer.py`: Async producer wrapper (7 tests)
- `tests/test_state_consumer.py`: ORM models + Snapshot pattern (8 tests)
- `tests/test_backfill.py`: Incremental gap detection (6 tests)
- `tests/test_queries.py`: Confidence calculation + premium guard (11 tests)
- `tests/test_tx_hunter.py`: RBF/CPFP calculations + classification (10 tests)

## Documentation

- [Architecture Guide](docs/architecture.md) - System design and component breakdown
- [Data Dictionary](docs/data_dictionary.md) - Metric definitions, calculations, and data lineage
- [Decision Log](docs/decisions.md) - Architectural decisions and project journal
- [Strategy Roadmap](docs/strategy.md) - Product vision and phased roadmap

## Development Workflow

```bash
just --list  # Show all available commands
```

**Lead Engineer:** Israel (@ieshatchuell)