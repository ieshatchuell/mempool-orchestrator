Mempool Orchestrator

An agentic data platform designed to ingest, process, and optimize Bitcoin mempool dynamics for automated treasury management.

## Tech Stack
- **Runtime:** Python 3.12+ (managed by `uv`)
- **Event Broker:** Redpanda (Kafka-compatible)
- **Database:** DuckDB (OLAP Storage)
- **AI/LLM:** Ollama + Llama 3.2 (Local Inference)
- **Agent Framework:** PydanticAI (Structured Workflows)
- **Analytics UI:** Streamlit (Real-time Dashboard)
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

```python
IF fee_premium_pct > 20%:
    action = WAIT         # Target: Historical Median Fee
ELSE:
    action = BROADCAST    # Target: Current Median Fee
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
DUCKDB_PATH=mempool_data.duckdb
DUCKDB_BATCH_SIZE=50
AGENT_HISTORY_PATH=agent_history.duckdb
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

# 6. Start AI Infrastructure (Ollama + Orchestrator)
just ai-up

# 7. View Orchestrator Logs
just ai-logs

# 8. Stop AI Infrastructure
just ai-down

# 9. Stop Infrastructure
just infra-down
```

## 📊 Data Access & Architecture

The system implements a **Hybrid Architecture** combining local processes for speed with containerized AI for isolation.

### 1. Hybrid Architecture

| Layer | Runtime | Purpose |
|-------|---------|--------|
| **Ingestion** | Local (uv) | Low-latency WebSocket streaming |
| **Storage** | Local (uv) | DuckDB writes with file locking |
| **AI Orchestrator** | Docker | Isolated LLM inference environment |
| **Ollama** | Docker | Local Llama 3.2 model serving |

> **Critical Pattern:** The Dockerized Orchestrator reads `mempool_data.duckdb` via a **Read-Only Volume Mount** (`:ro`) while the local Storage process writes to it. This prevents file locking conflicts.

### 2. Data Flow
- **Radar (WebSocket):** Real-time signals from `mempool.space` for mempool stats and projected blocks.
- **Fetcher (REST API):** On-demand fetching of confirmed block data for auditing and backfill.
- **Vault (DuckDB):** Typed storage with Pydantic validation at ingestion boundary.
- **Brain (Orchestrator):** Neuro-Symbolic agent: Python computes decisions, Llama 3.2 generates explanations.
- **Agent Memory:** Dedicated `agent_history.duckdb` for storing decision logs (Action, Reasoning, Fee) to ensure auditability and avoid write conflicts.

### 3. Typed Schema (Silver Layer)

The system uses **strongly-typed tables** with Pydantic validation:

**`mempool_stats` table**
- `ingestion_time`: TIMESTAMP (UTC)
- `size`: UINTEGER (transaction count)
- `bytes`: UINTEGER (total mempool size)
- `total_fee`: UBIGINT (fees in Satoshis)
- `min_fee`: DOUBLE (minimum fee rate to enter mempool)

**`projected_blocks` table**
- `ingestion_time`: TIMESTAMP (UTC)
- `block_index`: UTINYINT (0=next block, 1=following, etc.)
- `block_size`: UINTEGER (bytes)
- `block_v_size`: DOUBLE (virtual size, can include fractional values)
- `n_tx`: UINTEGER (transaction count)
- `total_fees`: UBIGINT (fees in Satoshis)
- `median_fee`: DOUBLE (median fee rate)
- `fee_range`: JSON (array of fee rates: [min, p10, p25, p50, p75, p90, max])

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
# Query mempool stats
uv run python -c "import duckdb; conn = duckdb.connect('mempool_data.duckdb', read_only=True); print(conn.execute('SELECT * FROM mempool_stats ORDER BY ingestion_time DESC LIMIT 10').df())"

# Query projected blocks (most recent snapshot)
uv run python -c "import duckdb; conn = duckdb.connect('mempool_data.duckdb', read_only=True); print(conn.execute('SELECT ingestion_time, block_index, n_tx, total_fees, median_fee, fee_range FROM projected_blocks WHERE ingestion_time = (SELECT MAX(ingestion_time) FROM projected_blocks) ORDER BY block_index').df())"

# Audit data quality (verify block_index ordering and fee_range structure)
uv run python -c "import duckdb; conn = duckdb.connect('mempool_data.duckdb', read_only=True); print(conn.execute('SELECT ingestion_time, block_index, total_fees, fee_range FROM projected_blocks ORDER BY ingestion_time DESC LIMIT 5').df())"
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