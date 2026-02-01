# System Architecture

## 1. High-Level Data Flow (V4)
The system follows a **Hybrid Signal & Fetch** pattern with typed storage and real-time observability.

```
[External WebSocket: mempool.space] 
      |
      v (Async Streaming - "Radar")
[Ingestor: src.ingestors.mempool_ws] 
      |
      v (Internal Library)
[Producer: src.common.kafka_producer]
      |
      v (Kafka Protocol)
[Broker: Redpanda (Topic: mempool-raw)]
      |
      v (Manual Offset Commit)
[Consumer: src.storage.duckdb_consumer]
      |
      v (Batch Write + Pydantic Validation)
[Storage: DuckDB (mempool_data.duckdb)]
      |
      v (Read-Only Queries)
[Dashboard: Streamlit UI]

[External REST API: mempool.space/api]
      |
      v (On-Demand Fetch - "Fetcher")
[API Client: src.ingestors.mempool_api]
```

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
4. **Validation:** Fail-fast strategy. Invalid payloads are logged and dropped to protect downstream storage.

### B. Storage Layer (The "Vault")
- **Engine:** **DuckDB** (In-process OLAP).
- **Strategy:** Buffered Consumer (batch size: 50) with Pydantic validation.
- **Schema Strategy (Silver Layer):** Direct write to structured tables (no raw JSON dump).
    - `mempool_stats`: High-frequency metrics (ingestion_time, size, bytes, total_fee, min_fee).
    - `projected_blocks`: Template data (block_size, n_tx, total_fees, median_fee).
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
- **Implementation:** `dashboard.py`
  - **Framework:** Streamlit for rapid interactive UI development.
  - **Data Source:** Read-only connection to `mempool_data.duckdb`.
  - **Features:**
    - Real-time mempool statistics visualization
    - Projected block analytics
    - Historical trend analysis
    - Data quality monitoring
- **Launch:** `just dashboard`

### E. Common Infrastructure & Configuration
- **Kafka Wrapper:** `MempoolProducer` with non-blocking `poll(0)` and delivery callbacks.
- **Configuration:** `src/config.py` using Pydantic Settings. Enforces strict types and strips whitespace from environment variables.
  - `kafka_bootstrap_servers`: Kafka broker connection string
  - `mempool_topic`: Target Kafka topic
  - `mempool_ws_url`: WebSocket URL for real-time data
  - `mempool_api_url`: REST API base URL
  - `duckdb_path`: Database file path
  - `duckdb_batch_size`: Batch flush size

## 3. Package Structure Standards
- `src.common`: Shared infrastructure clients.
- `src.ingestors`: External data source connectors (WebSocket + REST API).
- `src.schemas`: Data contracts and Pydantic models.
- `src.storage`: Persistence logic.
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
    - `tests/test_api.py`: REST API client behavior (55 total tests).

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