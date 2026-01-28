Mempool Orchestrator

An agentic data platform designed to ingest, process, and optimize Bitcoin mempool dynamics for automated treasury management.

## Tech Stack
- **Runtime:** Python 3.12+ (managed by `uv`)
- **Event Broker:** Redpanda (Kafka-compatible)
- **Database:** DuckDB (OLAP Storage)
- **Data Science:** Pandas / NumPy (Auditing & Analysis)
- **Infrastructure:** Docker / OrbStack
- **IDE:** Antigravity (Gemini 3)

## 🤖 AI-Driven Development

This project operates under strict **Staff Data Engineer** constraints enforced by the AI Agent.

### Agent Configuration
The `.agent/` directory acts as "Infrastructure as Code" for the development workflow:
- **Persona:** Enforces architectural rigor, async-first coding, and FinOps awareness.
- **Domain Knowledge:** Pre-loaded with Bitcoin transaction structures and Redpanda limits (e.g., 1MB message cap).
- **Documentation:** For setup and rules, see [AI Workflow Guide](docs/setup/AI_WORKFLOW.md).

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
```bash
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
```

## 📊 Data Access & Architecture

The system implements a **Medallion Architecture** to ensure data quality and analytical performance.

### 1. Medallion Layers
- **Bronze (Raw):** Verbatim JSON payloads from the WebSocket stored in `raw_mempool`.
- **Silver (Parsed):** Structured metrics extracted via the `v_mempool_stats` view.

### 2. Data Samples

**Bronze Layer (`raw_mempool` table)**
```json
{
  "timestamp": "2026-01-25 20:13:31",
  "key": "stats",
  "data": {
    "mempoolInfo": {
      "size": 38446,
      "bytes": 19529746,
      "total_fee": 0.03449075
    }
  }
}
```

**Silver Layer (`v_mempool_stats` view)**

| timestamp | tx_count | total_bytes | total_fee_btc | avg_tx_fee_sats |
| :--- | :--- | :--- | :--- | :--- |
| 2026-01-25 20:13:31 | 38,446 | 19,529,746 | 0.034491 | 89.71 |

### 3. Querying the Data
You can audit the structured data directly from your terminal using Python/DuckDB in read-only mode:

```bash
uv run python -c "import duckdb; conn = duckdb.connect('mempool_data.duckdb', read_only=True); print(conn.execute('SELECT * FROM v_mempool_stats ORDER BY timestamp DESC LIMIT 10').df())"
```