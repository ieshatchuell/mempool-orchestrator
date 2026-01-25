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

### A. Ingestion Layer (The "Radar")
- **Configuration:** Managed via **Pydantic Settings**. Loads environment variables from `.env` with strict type validation.
- **Routing Logic:** Python 3.12 Structural Pattern Matching (`match/case`) for declarative event classification.
- **Protocol:** JSON-RPC over WebSockets. Actions: `init` + `want` (stats, mempool-blocks).

### B. Storage Layer (The "Vault")
- **Engine:** **DuckDB** (In-process OLAP).
- **Strategy:** Buffered Consumer with batch writes (50 records) and **At-Least-Once** delivery semantics.
- **Data Modeling (Medallion Pattern):**
    - **Bronze (Raw):** `raw_mempool` table containing full JSON payloads.
    - **Silver (Parsed):** `v_mempool_stats` view for structured metrics (TX count, bytes, usage, and corrected BTC fees).

### C. Common Infrastructure
- **Kafka Wrapper:** High-level abstraction over `confluent-kafka`.
- **Performance:** Non-blocking `poll(0)` for producers and manual commit management for consumers to ensure data integrity.

## 3. Package Structure Standards
- `src.common`: Shared infrastructure clients (Kafka).
- `src.ingestors`: External data source connectors.
- `src.storage`: Persistence logic and database consumers.
- `src.utils`: Stateless helper functions.

## 4. Developer Experience (DX) & Tooling
- **Package Manager:** `uv` (Fast resolver and environment manager).
- **Command Runner:** `Just` (Recipes for infra, radar, and storage).
- **Analysis:** `pandas` and `numpy` for terminal-based data auditing.