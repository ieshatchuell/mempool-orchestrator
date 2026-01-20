# Mempool Orchestrator

An agentic data platform designed to ingest, process, and optimize Bitcoin mempool dynamics for automated treasury management.

## Tech Stack
- **Runtime:** Python 3.12+ (managed by `uv`)
- **Event Broker:** Redpanda (Kafka-compatible)
- **Infrastructure:** Docker / OrbStack
- **Database:** DuckDB (Planned for Q1)

## Architecture
The system follows an event-driven architecture where mempool data is streamed into Redpanda topics, allowing asynchronous processing by specialized agents.



## 🚀 Quick Start

### Prerequisites
- **Python 3.12+** (managed via `uv`)
- **Docker** (via OrbStack recommended)
- **Just** (Command Runner): `brew install just`

### Commands
We use `just` to standardize all project operations.

```bash
# 1. Start Infrastructure (Redpanda)
just infra-up

# 2. System Health Check
just check

# 3. Run the Ingestion Pipeline (The "Radar")
just radar

# 4. Stop Infrastructure
just infra-down