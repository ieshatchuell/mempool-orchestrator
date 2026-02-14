# System Architecture

## 1. High-Level Data Flow (V5)
The system follows a **Decoupled Monorepo** pattern combining local processes for speed with containerized AI for isolation. The Frontend (Streamlit) is physically separated from the Backend (Data Engineering) to enable future migration to React without breaking pipelines.

```
┌─────────────────────────────────────────────────────────────────┐
│                     HOST MACHINE (Local Processes)              │
│                                                                 │
│  [External WebSocket: mempool.space]                            │
│        │                                                        │
│        v (Async Streaming - "Radar")                            │
│  [Ingestor: backend/src/ingestors/mempool_ws]                   │
│        │                                                        │
│        v (Internal Library)                                     │
│  [Producer: backend/src/common/kafka_producer]                  │
│        │                                                        │
│        v (Kafka Protocol)                                       │
│  ┌─────────────────┐    ┌──────────────────────────────────┐    │
│  │ Redpanda        │    │ data/market/mempool_data.duckdb  │    │
│  │ (Docker)        │───▶│ (Write Lock: Local Process)      │    │
│  └─────────────────┘    └────────────┬─────────────────────┘    │
│                                      │                          │
└──────────────────────────────────────│──────────────────────────┘
                                       │ :ro volume mount
┌──────────────────────────────────────│──────────────────────────┐
│                     DOCKER NETWORK   │                          │
│                                      v                          │
│  ┌─────────────────┐    ┌──────────────────────────────────┐    │
│  │ Ollama          │◀───│ Orchestrator                     │    │
│  │ (Llama 3.2)     │    │ (Read-Only DuckDB Access)        │    │
│  └─────────────────┘    └──────────────────────────────────┘    │
│                                      │                          │
│                                      v :rw volume mount         │
│                         ┌──────────────────────────────────┐    │
│                         │ data/history/agent_history.duckdb│    │
│                         └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Concurrency Pattern: Writer + Reader Isolation

| Component | Runtime | Access Mode | Purpose |
|-----------|---------|-------------|---------|
| Storage Consumer | Local (uv) | **Write** | Kafka → DuckDB persistence |
| AI Orchestrator | Docker | **Read-Only** | Query DuckDB via `:ro` mount |

> **Critical:** The Orchestrator uses `read_only=True` when connecting to DuckDB, preventing write lock conflicts with the local Storage process.

[External REST API: mempool.space/api]
      |
      v (On-Demand Fetch - "Fetcher")
[API Client: src.ingestors.mempool_api]

## 2. Component Breakdown

### A. Ingestion Layer (The "Radar") - Real-Time Event Filtering
The Radar pattern provides a lightweight, metadata-first approach to ingesting Bitcoin mempool data.

#### Data Contracts & Validation
- **Schema Definition:** `src/schemas.py`
  - Pydantic v2 models with `strict=True` for compile-time type safety.
  - **Monetary Precision:** All values (`fees`, `totalFees`) are strictly `int` (Satoshis) - NEVER float.
  - **Alias Mapping:** Automatic camelCase ↔ snake_case conversion via `alias_generator=to_camel`.
  - **Models:**
    - `MempoolStats`: Real-time mempool state (size, bytes, fees).
    - `MempoolBlock`: Projected block statistics (blockSize, medianFee, feeRange).
    - `Transaction`: Full transaction schema for REST API integration.

#### Radar Ingestion Pattern
**Source:** Mempool.space WebSocket API (`wss://mempool.space/api/v1/ws`)

**Event Routing Logic** (`src/ingestors/mempool_ws.py`):
1. **Silent Filter:** `conversions` messages are dropped (noise).
2. **Stats Events:** Key `mempoolInfo` → Validated as `MempoolStats` → Kafka key: `stats`.
3. **Block Events:** Key `mempool-blocks` → Validated as `List[MempoolBlock]` → Kafka key: `mempool_block`.
4. **Confirmed Blocks (Signal & Fetch):** Key `block` → REST fetch `GET /api/v1/block/{hash}` → Validated as `ConfirmedBlock` → Kafka key: `confirmed_block`.
5. **Validation:** Fail-fast strategy. Invalid payloads are logged and dropped to protect downstream storage.

### B. Storage Layer (The "Vault")
- **Engine:** **DuckDB** (In-process OLAP).
- **Strategy:** Buffered Consumer (batch size: 50) with Pydantic validation.
- **Schema Strategy (Silver Layer):** Direct write to structured tables (no raw JSON dump).
    - `mempool_stats`: High-frequency metrics (ingestion_time, size, bytes, total_fee, min_fee).
    - `mempool_stream`: Speculative projected blocks from WebSocket (block_index, block_size, n_tx, total_fees, median_fee).
    - `block_history`: Confirmed mined blocks (height, block_hash, block_size, n_tx, total_fees, median_fee, pool_name).
- **Data Types:** Strict mapping. Fees are stored as `UBIGINT` (Satoshis) to prevent floating-point errors.

### C. The Fetcher (REST Client)
- **Purpose:** On-demand fetching of confirmed block data for auditing and historical backfill.
- **Implementation:** `src/ingestors/mempool_api.py`
  - **Client:** `httpx.AsyncClient` for async HTTP requests.
  - **Configuration:** Reads base URL from `settings.mempool_api_url` (no hardcoding).
  - **Error Handling:** Custom `MempoolAPIError` for HTTP failures (4xx, 5xx), network errors, and JSON parsing issues.
  - **Context Manager:** Proper resource management with `async with MempoolAPI()`.
- **Methods:**
  - `get_block_stats(block_hash: str) -> dict`: Fetch block header data from `/block/{hash}`.
- **Testing:** Comprehensive test suite (`tests/test_api.py`) using `respx` to mock HTTP requests (13 tests).

### D. The Dashboard
- **Purpose:** Real-time observability and data auditing interface.
- **Implementation:** `frontend/app/main.py`
  - **Framework:** Streamlit for rapid interactive UI development.
  - **Data Source:** Read-only connection to `data/market/mempool_data.duckdb`.
  - **Decoupling:** Fully independent from backend; uses `os.getenv()` for configuration.
  - **Features:**
    - **KPIs:** Mempool size (txs), current median fee (sat/vB), pending fees (BTC), blocks to clear.
    - **Blocks Table:** Last 10 projected blocks (`block_index=0`) with fees, tx count, and block size.
    - **Fee Trend Chart:** Historical `median_fee` from confirmed blocks (`block_history`).
    - **Strategy Simulator:** Interactive strategy selector (SMA-20, EMA-20, Orchestrator) with overlay chart comparing strategy recommendations against actual fees, plus KPIs (cumulative cost, slippage, hit rate). Powered by `src.strategies` module.
    - **Graceful Degradation:** Shows offline status and guidance when DuckDB is unavailable.
- **Launch:** `just dashboard`

### E. The Orchestrator (Neuro-Symbolic Brain)

The Orchestrator implements a **Safe-Guarded Hybrid AI** pattern:

```
┌────────────────────────────────────────────────────────────────┐
│                    DECISION PIPELINE                           │
│                                                                │
│  MempoolContext ─────┐                                         │
│  (from DuckDB)       │                                         │
│                      v                                         │
│              ┌───────────────────┐                             │
│              │ evaluate_market   │  LAYER 1: PYTHON (Critical) │
│              │ _rules()          │  - Deterministic            │
│              └─────────┬─────────┘  - Zero latency             │
│                        │                                       │
│                        v                                       │
│              ┌───────────────────┐                             │
│              │ MarketDecision    │  (action, recommended_fee)  │
│              └─────────┬─────────┘                             │
│                        │                                       │
│                        v                                       │
│              ┌───────────────────┐                             │
│              │ get_ai_reasoning()│  LAYER 2: LLM (Non-Critical)│
│              │ via Llama 3.2    │  - Generates commentary      │
│              └─────────┬─────────┘  - Fallback if unavailable  │
│                        │                                       │
│                        v                                       │
│              ┌───────────────────┐                             │
│              │ AgentDecision     │  Final output with reasoning│
│              └───────────────────┘                             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### The Sidecar Pattern

The AI acts as a **non-critical sidecar**:

| Scenario | Python Logic | AI Narrative | Result |
|----------|-------------|--------------|--------|
| Normal | ✅ Computes decision | ✅ Generates reasoning | Full decision + explanation |
| AI Timeout | ✅ Computes decision | ⏱️ Timeout (30s) | Decision + fallback text |
| AI Offline | ✅ Computes decision | ❌ Error caught | Decision + fallback text |

> **Key Insight:** The system **never fails** to make a decision. The LLM provides "nice to have" commentary but cannot block the critical path.

#### Performance Characteristics

| Metric | Pure LLM (v1) | Neuro-Symbolic (v2) |
|--------|--------------|---------------------|
| Decision Latency | ~40s | ~1.3s |
| JSON Parse Errors | Frequent | Zero |
| Arithmetic Errors | Occasional | Zero |
| Graceful Degradation | ❌ | ✅ |

### F. Common Infrastructure & Configuration
- **Kafka Wrapper:** `MempoolProducer` with non-blocking `poll(0)` and delivery callbacks.
- **Configuration:** `src/config.py` using Pydantic Settings. Enforces strict types and strips whitespace from environment variables.
  - `kafka_bootstrap_servers`: Kafka broker connection string
  - `mempool_topic`: Target Kafka topic
  - `mempool_ws_url`: WebSocket URL for real-time data
  - `mempool_api_url`: REST API base URL
  - `duckdb_path`: Database file path
  - `duckdb_batch_size`: Batch flush size
  - `agent_history_path`: Agent decision history database

### G. Persistence Layer (Strict Data Isolation)

The system implements a **Strict Data Isolation** pattern with physically separated databases:

| Database | Path | Writer | Reader | Mount |
|----------|------|--------|--------|-------|
| Market Data | `data/market/mempool_data.duckdb` | Storage Service (Local) | Orchestrator (Docker) | `:ro` |
| Agent Memory | `data/history/agent_history.duckdb` | Orchestrator (Docker) | Auditing/Backtest | `:rw` |

> **Key Insight:** Separating RO and RW data into distinct directories enables strict Docker volume permissions. The `market/` folder is mounted read-only, while `history/` is mounted read-write.

**Schema (`decision_history` table):**
- `timestamp`: TIMESTAMP (UTC)
- `action`: VARCHAR (WAIT/BROADCAST)
- `current_fee`: UBIGINT (sat/vB)
- `recommended_fee`: UBIGINT (sat/vB)
- `ai_confidence`: DOUBLE (0.0-1.0)
- `ai_reasoning`: VARCHAR (LLM explanation)
- `model_version`: VARCHAR (e.g., "neuro-symbolic-v1")

> **Connection Strategy:** `AgentHistory` keeps a persistent DuckDB connection (opened once in `__init__`, closed explicitly via `close()`). This is safe because the orchestrator is the sole writer to this file.

## 3. Package Structure Standards
- `src.common`: Shared infrastructure clients.
- `src.ingestors`: External data source connectors (WebSocket + REST API).
- `src.schemas`: Data contracts and Pydantic models.
- `src.storage`: Persistence logic.
- `src.strategies`: Fee strategy functions (naive, SMA, EMA, orchestrator) — shared by dashboard and backtest.
- `src.utils`: Stateless helpers.

## 4. Developer Experience (DX) & Quality Assurance
- **Manager:** `uv`.
- **Runner:** `Just`.
- **Testing Stack:**
  - **Framework:** `pytest` (Root configuration in `pyproject.toml`).
  - **Mocks:** `pytest-mock` and `unittest.mock` for isolating Kafka and WebSocket logic.
  - **HTTP Mocking:** `respx` for REST API testing.
  - **Async:** `pytest-asyncio` for coroutine testing.
  - **Coverage:**
    - `tests/test_schemas.py`: Contract validation (Happy/Sad paths).
    - `tests/test_ingestor.py`: Routing logic and error handling.
    - `tests/test_kafka_producer.py`: Infrastructure wrapper behavior.
    - `tests/test_config.py`: Environment variable loading and validation.
    - `tests/test_api.py`: REST API client behavior.
    - `tests/test_agent_history.py`: Agent decision persistence.
    - *66 total tests.*

## 5. Architectural Patterns

### Hybrid Signal & Fetch
- **Signal (WebSocket):** Low-latency stream for mempool state changes.
- **Fetch (REST API):** On-demand retrieval for confirmed blocks and historical data.
- **Rationale:** Avoids message size limits on Kafka (1MB default) and provides data completeness.

### Medallion Architecture (Simplified)
- **Bronze Layer:** Eliminated (direct validation at ingestion boundary).
- **Silver Layer:** Structured, typed tables with Pydantic validation.
- **Gold Layer:** Future analytical views and aggregations.

### Data Validation Strategy
- **Boundary Validation:** All external data validated with Pydantic at ingestion.
- **Type Safety:** Strict mode enforced (`strict=True`).
- **Monetary Precision:** Integer-only for fees (Satoshis) to prevent floating-point errors.