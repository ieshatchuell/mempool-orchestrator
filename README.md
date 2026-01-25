# Mempool Orchestrator

An agentic data platform designed to ingest, process, and optimize Bitcoin mempool dynamics for automated treasury management.

## Tech Stack
- **Runtime:** Python 3.12+ (managed by `uv`)
- **Event Broker:** Redpanda (Kafka-compatible)
- **Database:** DuckDB (OLAP Storage)
- **Data Science:** Pandas / NumPy (Auditing & Analysis)
- **Infrastructure:** Docker / OrbStack

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
DUCKDB_PATH=mempool_data.duckdb
DUCKDB_BATCH_SIZE=50
```

### Commands

# 1. Start Infrastructure (Redpanda)
just infra-up

# 2. System Health Check
just check

# 3. Launch Ingestion Pipeline (The "Radar")
just radar

# 4. Launch Storage Consumer (The "Vault")
just storage

# 5. Stop Infrastructure
just infra-down

📊 Data Access & Architecture
The system implements a Medallion Architecture to ensure data quality and analytical performance.

1. Storage Engine
Data is persisted in a local mempool_data.duckdb file. This file is ignored by Git to prevent bloating the repository with binary data.

2. Medallion Layers
Bronze (Raw): Verbatim JSON payloads from the WebSocket stored in the raw_mempool table.

Silver (Parsed): Structured metrics extracted via the v_mempool_stats view.

3. Querying the Data
You can audit the structured data directly from your terminal using Python/DuckDB in read-only mode:

```bash
uv run python -c "import duckdb; conn = duckdb.connect('mempool_data.duckdb', read_only=True); print(conn.execute('SELECT * FROM v_mempool_stats ORDER BY timestamp DESC LIMIT 10').df())"
```

The Silver Layer provides human-readable columns such as timestamp, tx_count, total_fee_btc, and avg_tx_fee_sats.