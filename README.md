Mempool Orchestrator

An agentic data platform designed to ingest, process, and optimize Bitcoin mempool dynamics for automated treasury management.

## Tech Stack
- **Runtime:** Python 3.12+ (managed by `uv`)
- **Event Broker:** Redpanda (Kafka-compatible)
- **Database:** DuckDB (OLAP Storage)
- **Analytics UI:** Streamlit (Real-time Dashboard)
- **Data Science:** Pandas / NumPy (Auditing & Analysis)
- **Infrastructure:** Docker / OrbStack
- **IDE:** Antigravity (Gemini 3)

## 🤖 AI-Driven Development

This project operates under strict **Staff Data Engineer** constraints enforced by the AI Agent.

### Agent Configuration
The `.agent/` directory acts as "Infrastructure as Code" for the development workflow:
- **Persona:** Enforces architectural rigor, async-first coding, and FinOps awareness.
- **Domain Knowledge:** Pre-loaded with Bitcoin transaction structures and Redpanda limits (e.g., 1MB message cap).

## 🚀 Quick Start

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
DUCKDB_PATH=mempool_data.duckdb
DUCKDB_BATCH_SIZE=50
```

### Commands
```bash
# 1. Start Infrastructure (Redpanda)
just infra-up

# 2. System Health Check
just check

# 3. Launch Ingestion Pipeline (The "Radar")
just radar

# 4. Launch Storage Consumer (The "Vault")
just storage

# 5. Launch Analytics Dashboard
just dashboard

# 6. Stop Infrastructure
just infra-down
```

## 📊 Data Access & Architecture

The system implements a **Hybrid Signal & Fetch Architecture** with typed storage for analytical performance.

### 1. Hybrid Architecture
- **Radar (WebSocket):** Real-time signals from `mempool.space` for mempool stats and projected blocks.
- **Fetcher (REST API):** On-demand fetching of confirmed block data for auditing and backfill.
- **Vault (DuckDB):** Typed storage with Pydantic validation at ingestion boundary.

### 2. Typed Schema (Silver Layer)

The system uses **strongly-typed tables** with Pydantic validation:

**`mempool_stats` table**
- `ingestion_time`: TIMESTAMP (UTC)
- `size`: UINTEGER (transaction count)
- `bytes`: UINTEGER (total mempool size)
- `total_fee`: UBIGINT (fees in Satoshis)
- `min_fee`: DOUBLE (minimum fee rate to enter mempool)

**`projected_blocks` table**
- `ingestion_time`: TIMESTAMP (UTC)
- `block_size`: UINTEGER (bytes)
- `block_v_size`: UINTEGER (virtual size)
- `n_tx`: UINTEGER (transaction count)
- `total_fees`: UBIGINT (fees in Satoshis)
- `median_fee`: DOUBLE (median fee rate)

> **Note:** All monetary values are stored as `UBIGINT` (unsigned big integers) in **Satoshis** to prevent floating-point precision errors.

### 3. Data Sample

| ingestion_time | size | bytes | total_fee | min_fee |
| :--- | :--- | :--- | :--- | :--- |
| 2026-02-01 01:23:45 | 38,446 | 19,529,746 | 3,449,075 | 1.2 |

### 4. Querying the Data

**From Terminal (Read-Only):**
```bash
uv run python -c "import duckdb; conn = duckdb.connect('mempool_data.duckdb', read_only=True); print(conn.execute('SELECT * FROM mempool_stats ORDER BY ingestion_time DESC LIMIT 10').df())"
```

**From Dashboard:**
```bash
just dashboard
```

## 🧪 Testing

The project maintains comprehensive test coverage with strict mocking:

```bash
# Run all tests
just test

# Run specific test suite
uv run pytest tests/test_api.py -v
```

**Test Coverage:**
- `tests/test_schemas.py`: Pydantic contract validation
- `tests/test_ingestor.py`: WebSocket routing logic
- `tests/test_kafka_producer.py`: Kafka wrapper behavior
- `tests/test_config.py`: Environment variable validation
- `tests/test_api.py`: REST API client (httpx + respx mocking)

## 📚 Documentation

- [Architecture Guide](docs/architecture.md) - System design and component breakdown
- [Decision Log](docs/decisions.md) - Architectural decisions and project journal

## 🔧 Development Workflow

This project follows a "Just-driven" workflow. All commands are defined in the `Justfile`:

```bash
just --list  # Show all available commands
```

Key recipes:
- `just check` - System health verification
- `just test` - Run test suite
- `just radar` - Start WebSocket ingestor
- `just storage` - Start DuckDB consumer
- `just dashboard` - Launch analytics UI