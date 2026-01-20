# Mempool Orchestrator

An agentic data platform designed to ingest, process, and optimize Bitcoin mempool dynamics for automated treasury management.

## Tech Stack
- **Runtime:** Python 3.12+ (managed by `uv`)
- **Event Broker:** Redpanda (Kafka-compatible)
- **Infrastructure:** Docker / OrbStack
- **Database:** DuckDB (Planned for Q1)

## Architecture
The system follows an event-driven architecture where mempool data is streamed into Redpanda topics, allowing asynchronous processing by specialized agents.



## Getting Started

### Prerequisites
- OrbStack or Docker Desktop
- Homebrew

### Infrastructure Setup
```bash
cd infra
docker compose up -d
```

### Verification Command Breakdown

The following command ensures the Redpanda broker is operational and reachable:

```bash
docker exec -it infra-redpanda-1 rpk cluster health

Why we run this:

Connectivity: Confirms the Docker network is correctly routing traffic to the broker.

Node Status: Verifies that the Redpanda process is healthy and the storage engine is initialized.

Leader Election: Ensures the cluster (even as a single-node) has a designated leader to manage data streams.

Expected Output: You should see a status report showing HEALTHY. If it returns an error, check the container logs using docker logs infra-redpanda-1.