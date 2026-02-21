Mempool Orchestrator

An agentic data platform designed to ingest, process, and optimize Bitcoin mempool dynamics for automated treasury management.

## Tech Stack
- **Runtime:** Python 3.12+ (managed by `uv`)
- **Event Broker:** Redpanda (Kafka-compatible)
- **OLAP Database:** DuckDB (Write-optimized OLAP storage)
- **Read Cache:** Redis (CQRS read layer for dashboard API)
- **Web API:** FastAPI (Redis-backed, sub-ms reads)
- **Frontend:** Next.js + shadcn/ui (React dashboard)
- **AI/LLM:** Ollama + Llama 3.2 (Local Inference)
- **Agent Framework:** PydanticAI (Structured Workflows)
- **Data Science:** Pandas / NumPy (Auditing & Analysis)
- **Infrastructure:** Docker / OrbStack
- **IDE:** Antigravity (Gemini 3)

## 🧠 Neuro-Symbolic Architecture

The Orchestrator implements a **Safe-Guarded Hybrid AI** pattern for maximum reliability:

| Layer | Engine | Responsibility | Latency |
|-------|--------|----------------|--------|
| **Logic (Δ)** | Python | Deterministic rules (thresholds, math) | ~0ms |
| **Narrative (N)** | Llama 3.2 | Human-readable reasoning (non-critical) | ~1.3s |

### Key Benefits

- **⚡ ~30x Faster**: From ~40s (pure LLM) to ~1.3s (hybrid)
- **🔒 100% Stable**: Python logic never fails; LLM is "sidecar" commentary
- **🛡️ Graceful Degradation**: If AI is offline, decisions continue with fallback text

### Decision Rules (Deterministic)

The orchestrator supports two strategy modes via `STRATEGY_MODE` env var:

**🐢 PATIENT** (default) — Treasury operations, saves ~27.7%:
```python
IF fee_premium_pct > 20%:
    action = WAIT         # Target: Historical Median Fee
ELSE:
    action = BROADCAST    # Target: Current Median Fee

# EMA trend adjusts confidence (secondary signal):
# RISING + WAIT → boost confidence | FALLING + BROADCAST → boost confidence
```

**⚡ RELIABLE** — Time-sensitive operations, 94% hit rate:
```python
action = BROADCAST        # Always, with EMA-20 smoothed fee
```

> **Critical:** The LLM **never** makes decisions. It only explains decisions already made by Python.

## 🚀 Quick Start

### Prerequisites
- **Python 3.12+** (managed via `uv`)
- **Docker** (via OrbStack recommended)
- **Just** (Command Runner)
- **Ollama** (optional, for local LLM inference)

### Configuration
Create a `.env` file in the project root:
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MEMPOOL_TOPIC=mempool-raw
MEMPOOL_WS_URL=wss://mempool.space/api/v1/ws
MEMPOOL_API_URL=https://mempool.space/api
DUCKDB_PATH=data/market/mempool_data.duckdb
DUCKDB_BATCH_SIZE=50
AGENT_HISTORY_PATH=data/history/agent_history.duckdb
STRATEGY_MODE=PATIENT  # PATIENT (treasury, -27.7%) or RELIABLE (time-sensitive, 94% hit)
```

### Project Structure
```text
├── backend/       # Data Engineering (Python, Kafka, DuckDB)
├── frontend/      # UI (Streamlit, Plotly)
├── data/          # State Storage
│   ├── market/    # Read-Only (Mempool data)
│   └── history/   # Read-Write (Agent decisions)
├── infra/         # Docker & Redpanda
└── scripts/       # Utilities
```

### Installation
```bash
# Sync all dependencies (recommended)
just sync

# Or sync individually
cd backend && uv sync
cd frontend && uv sync
```

### Commands
```bash
# 1. Start Infrastructure (Redpanda + Redis)
just infra-up

# 2. System Health Check
just check

# 3. Launch Ingestion Pipeline (The "Radar")
just radar

# 4. Launch Storage Consumer (The "Vault" → DuckDB + Redis projection)
just storage

# 5. Launch API Server (reads from Redis)
just api

# 6. Launch Next.js Dashboard
just dashboard

# 7. Start AI Infrastructure (Ollama + Orchestrator)
just ai-up

# 8. View Orchestrator Logs
just ai-logs

# 9. Stop AI Infrastructure
just ai-down

# 10. Stop Infrastructure
just infra-down
```

## 📊 Data Access & Architecture

The system implements a **Hybrid Architecture** combining local processes for speed with containerized AI for isolation.

### 1. CQRS Hybrid Architecture

| Layer | Runtime | Purpose |
|-------|---------|--------|
| **Ingestion** | Local (uv) | Low-latency WebSocket streaming |
| **Storage** | Local (uv) | DuckDB writes + Redis projection |
| **API** | Local (uv) | FastAPI reads from Redis (sub-ms) |
| **AI Orchestrator** | Docker | Isolated LLM inference environment |
| **Ollama** | Docker | Local Llama 3.2 model serving |

> **Architecture (ADR-013):** FastAPI never touches DuckDB. After each batch write, the Storage Consumer projects pre-computed dashboard views to Redis (~10 KB). The API serves these projections with sub-millisecond latency. If Redis has no data (cold start), the API returns valid empty-state defaults.

### 2. Data Flow
- **Radar (WebSocket):** Real-time signals from `mempool.space` for mempool stats and projected blocks.
- **Fetcher (REST API):** On-demand fetching of confirmed block data for auditing and backfill.
- **Vault (DuckDB):** Typed OLAP storage with Pydantic validation at ingestion boundary.
- **Redis (CQRS):** In-memory read layer. Storage projects 5 dashboard views after each flush.
- **API (FastAPI):** Reads from Redis, validates with Pydantic, serves JSON to the Next.js frontend.
- **Brain (Orchestrator):** Neuro-Symbolic agent: Python computes decisions, Llama 3.2 generates explanations.
- **Watchlist:** Track specific TXIDs by role (SENDER/RECEIVER). REST polling via `GET /api/tx/{txid}` detects confirmations.
- **Dust Watch:** Alerts when EMA fee drops below 5 sat/vB — signals a UTXO consolidation window.
- **RBF Advisor:** When a tracked SENDER tx is stuck, calculates the optimal replacement fee (BIP-125). Uses `recommended_fee` from the strategy engine.
- **CPFP Advisor:** When a tracked RECEIVER tx is stuck, calculates the child fee needed to unstick it (Package Relay). Uses `recommended_fee` from the strategy engine.
- **Strategy Engine:** Reusable `strategies.py` module powers both CLI backtesting and dashboard simulation.

### 3. Typed Schema (Silver Layer)

The system uses **strongly-typed tables** with Pydantic validation:

**`mempool_stats` table**
- `ingestion_time`: TIMESTAMP (UTC)
- `size`: UINTEGER (transaction count)
- `bytes`: UINTEGER (total mempool size)
- `total_fee`: UBIGINT (fees in Satoshis)
- `min_fee`: DOUBLE (minimum fee rate to enter mempool)

**`mempool_stream` table** (projected blocks from WebSocket)
- `ingestion_time`: TIMESTAMP (UTC)
- `block_index`: UTINYINT (0=next block, 1=following, etc.)
- `block_size`: UINTEGER (bytes)
- `block_v_size`: DOUBLE (virtual size, can include fractional values)
- `n_tx`: UINTEGER (transaction count)
- `total_fees`: UBIGINT (fees in Satoshis)
- `median_fee`: DOUBLE (median fee rate)
- `fee_range`: JSON (array of fee rates: [min, p10, p25, p50, p75, p90, max])

**`block_history` table** (confirmed blocks via REST API)
- `ingestion_time`: TIMESTAMP (UTC)
- `height`: UINTEGER (block height)
- `hash`: VARCHAR (block hash)
- `pool_name`: VARCHAR (mining pool)
- `n_tx`: UINTEGER (transaction count)
- `total_fees`: UBIGINT (fees in Satoshis)
- `median_fee`: DOUBLE (median fee rate)
- `fee_range`: JSON (array of fee rates)

> **Note:** All monetary values are stored as `UBIGINT` (unsigned big integers) in **Satoshis** to prevent floating-point precision errors.

### 4. Real WebSocket Payload Examples

**Mempool Stats Event (`stats`):**
```json
{
  "mempoolInfo": {
    "size": 38446,
    "bytes": 19529746,
    "usage": 25000000,
    "totalFee": 0.03449075,
    "mempoolMinFee": 1.2,
    "minRelayTxFee": 1.0
  }
}
```

**Projected Blocks Event (`mempool-blocks`):**
```json
{
  "mempool-blocks": [
    {
      "blockSize": 1595783,
      "blockVSize": 997994,
      "nTx": 3888,
      "totalFees": 2036508,
      "medianFee": 1.2053369765340756,
      "feeRange": [0.14, 0.14, 0.15, 1.20, 2.29, 3.29, 178.72]
    },
    {
      "blockSize": 1523456,
      "blockVSize": 945123,
      "nTx": 3654,
      "totalFees": 1856234,
      "medianFee": 1.15,
      "feeRange": [0.12, 0.13, 0.14, 1.15, 2.10, 3.15, 165.50]
    }
  ]
}
```

### 5. Querying the Data

**From Terminal (Read-Only):**
```bash
# Query mempool stats (from project root)
uv run python -c "import duckdb; conn = duckdb.connect('data/market/mempool_data.duckdb', read_only=True); print(conn.execute('SELECT * FROM mempool_stats ORDER BY ingestion_time DESC LIMIT 10').df())"

# Query projected blocks (most recent snapshot)
uv run python -c "import duckdb; conn = duckdb.connect('data/market/mempool_data.duckdb', read_only=True); print(conn.execute('SELECT ingestion_time, block_index, n_tx, total_fees, median_fee, fee_range FROM mempool_stream WHERE ingestion_time = (SELECT MAX(ingestion_time) FROM mempool_stream) ORDER BY block_index').df())"

# Query confirmed block history
uv run python -c "import duckdb; conn = duckdb.connect('data/market/mempool_data.duckdb', read_only=True); print(conn.execute('SELECT height, median_fee, pool_name FROM block_history ORDER BY height DESC LIMIT 10').df())"

# Run Scientific Backtest (compare 4 fee strategies)
cd backend && uv run python ../scripts/backtest.py
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

# Run specific test suite (from backend directory)
cd backend && uv run pytest tests/test_api.py -v
```

**Test Coverage:**
- `tests/test_schemas.py`: Pydantic contract validation
- `tests/test_ingestor.py`: WebSocket routing logic
- `tests/test_kafka_producer.py`: Kafka wrapper behavior
- `tests/test_config.py`: Environment variable validation
- `tests/test_api.py`: REST API client (httpx + respx mocking)
- `tests/test_orchestrator.py`: Dual-mode strategy engine (PATIENT/RELIABLE + EMA)
- `tests/test_strategies.py`: Pure fee strategy functions (naive, SMA, EMA, orchestrator)
- `tests/test_agent_history.py`: Decision persistence layer
- `tests/test_watchlist.py`: Watchlist CRUD, schema, validation, status transitions
- `tests/test_advisors.py`: RBF fee calculation (BIP-125), CPFP child fee (Package Relay), stuck detection

## 📚 Documentation

- [Architecture Guide](docs/architecture.md) - System design and component breakdown
- [Decision Log](docs/decisions.md) - Architectural decisions and project journal
- [Strategy Roadmap](docs/strategy.md) - Product vision and phased roadmap

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