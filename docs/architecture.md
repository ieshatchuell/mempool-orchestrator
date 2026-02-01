# System Architecture

## 1. High-Level Data Flow (V3)
The system follows a decoupled, event-driven streaming pattern with a Medallion Architecture for persistence.

[External WebSocket: mempool.space] 
      |
      v (Async Streaming)
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
      v (Batch Write: 50 records)
[Storage: DuckDB (mempool_data.duckdb)]

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
    - `Transaction`: Full transaction schema for future REST API integration.

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

### C. Common Infrastructure & Configuration
- **Kafka Wrapper:** `MempoolProducer` with non-blocking `poll(0)` and delivery callbacks.
- **Configuration:** `src/config.py` using Pydantic Settings. Enforces strict types and strips whitespace from environment variables.

## 3. Package Structure Standards
- `src.common`: Shared infrastructure clients.
- `src.ingestors`: External data source connectors.
- `src.schemas`: Data contracts and Pydantic models.
- `src.storage`: Persistence logic.
- `src.utils`: Stateless helpers.

## 4. Developer Experience (DX) & Quality Assurance
- **Manager:** `uv`.
- **Runner:** `Just`.
- **Testing Stack:**
  - **Framework:** `pytest` (Root configuration in `pyproject.toml`).
  - **Mocks:** `pytest-mock` and `unittest.mock` for isolating Kafka and WebSocket logic.
  - **Async:** `pytest-asyncio` for coroutine testing.
  - **Coverage:**
    - `tests/test_schemas.py`: Contract validation (Happy/Sad paths).
    - `tests/test_ingestor.py`: Routing logic and error handling.
    - `tests/test_kafka_producer.py`: Infrastructure wrapper behavior.
    - `tests/test_config.py`: Environment variable loading and validation.