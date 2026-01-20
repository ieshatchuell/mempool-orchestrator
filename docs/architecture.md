# System Architecture

## 1. High-Level Data Flow (V2)
The system follows a decoupled, event-driven streaming pattern.

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

## 2. Component Breakdown

### A. Ingestion Layer (The "Radar")
- **Runtime:** Python 3.12 managed by `uv`.
- **Concurrency:** `asyncio` loop for non-blocking I/O during WebSocket streaming.
- **Protocol:** JSON-RPC over WebSockets. Subscription actions: `want-stats` and `track-mempool`.
- **Execution Mode:** Module-based (`python -m`) to ensure absolute path resolution within the `src` namespace.

### B. Common Infrastructure Logic
- **Kafka Producer Wrapper:** A high-level abstraction over `confluent-kafka`.
- **Delivery Guarantees:** `acks=1` (leader acknowledgment) to balance throughput and data safety.
- **Performance:** Implements non-blocking `poll(0)` to process delivery reports asynchronously without stalling the ingestion loop.

### C. Message Broker (Redpanda)
- **Topic Strategy:** `mempool-raw`.
- **Keying Strategy:** - `stats`: Global mempool metrics.
    - `batch`: Real-time transaction clusters.
- **Isolation:** Operates within a dedicated Docker network (`infra_default`).

## 3. Package Structure Standards
To ensure scalability and maintain absolute imports, the project adheres to the following package structure:
- `src.common`: Shared infrastructure clients (Kafka, DBs).
- `src.ingestors`: External data source connectors.
- `src.utils`: Stateless helper functions.
- `__init__.py`: Mandatory markers in all directories to formalize Python namespaces.

## 4. Storage & Persistence (Upcoming)
- **Target:** DuckDB (Local OLAP).
- **Strategy:** A dedicated consumer module will subscribe to `mempool-raw`, perform schema validation (Pydantic), and persist flattened records into DuckDB.

## 5. Developer Experience (DX) & Tooling
- **Package Manager:** `uv` (Fast Python package installer & resolver).
- **Command Runner:** `Just` (Command standardization and abstraction).
- **Shell:** `zsh` + `Starship` (Context-aware prompt).