# System Architecture

## 1. High-Level Overview

The system implements an **Event-Driven Architecture (EDA)** with **Clean Architecture** layers. Data flows from the Bitcoin network through Kafka to PostgreSQL, and is served to the dashboard via a read-only FastAPI API.

```mermaid
graph LR
    subgraph External
        WS["mempool.space<br/>WebSocket API"]
        REST["mempool.space<br/>REST API"]
    end

    subgraph Workers
        ING["Ingestor<br/>(Radar)"]
        SC["State Consumer<br/>(Materializer)"]
    end

    subgraph Infrastructure
        RP["Redpanda<br/>(Kafka)"]
        PG["PostgreSQL 16<br/>(MVCC)"]
    end

    subgraph Presentation
        API["FastAPI<br/>(Read-Only)"]
        UI["Next.js<br/>(Dashboard)"]
    end

    WS -->|"async WS"| ING
    REST -->|"Signal & Fetch"| ING
    ING -->|"produce"| RP
    RP -->|"consume"| SC
    SC -->|"INSERT/UPSERT"| PG
    PG -->|"SELECT"| API
    API -->|"JSON"| UI
```

## 2. Clean Architecture Layers

The codebase follows strict dependency rules — inner layers never import from outer layers. All arrows flow **downward**: outer layers depend on inner layers, never the reverse.

```mermaid
graph TD
    subgraph PRESENTATION ["Presentation Layer"]
        direction LR
        M["api/main.py<br/><i>FastAPI Endpoints</i>"]
        Q["api/queries.py<br/><i>Async Queries</i>"]
        S["api/schemas.py<br/><i>Response Models</i>"]
    end

    subgraph APPLICATION ["Application Layer (Workers)"]
        direction LR
        W1["workers/ingestor.py<br/><i>WS → Kafka</i>"]
        W2["workers/state_consumer.py<br/><i>Kafka → PostgreSQL</i>"]
    end

    subgraph INFRASTRUCTURE ["Infrastructure Layer"]
        direction LR
        DB["database/<br/><i>SQLAlchemy 2.0 Async</i><br/>session.py · models.py"]
        MSG["messaging/<br/><i>aiokafka Producer</i><br/>producer.py"]
    end

    subgraph DOMAIN ["Domain Layer (Pure)"]
        D["domain/schemas.py<br/><i>Pydantic V2 Contracts</i><br/>Zero external deps"]
    end

    subgraph CORE ["Core"]
        C["core/config.py<br/><i>pydantic-settings</i>"]
    end

    %% Presentation → Infrastructure
    M --> Q
    M --> S
    Q --> DB

    %% Workers → Infrastructure + Domain
    W1 --> MSG
    W1 --> D
    W2 --> DB
    W2 --> D

    %% Infrastructure → Domain + Core
    DB --> C
    MSG --> C

    %% Cross-layer → Core
    M --> C

    style DOMAIN fill:#2d6a4f,color:#fff,stroke:#2d6a4f
    style CORE fill:#1b4332,color:#fff,stroke:#1b4332
    style INFRASTRUCTURE fill:#1a3a5c,color:#fff,stroke:#1a3a5c
    style APPLICATION fill:#7c4a1d,color:#fff,stroke:#7c4a1d
    style PRESENTATION fill:#3a3a3a,color:#fff,stroke:#3a3a3a
```

## 3. Data Flow (Detailed)

### 3.1 Ingestion Pipeline (The "Radar")

The Ingestor connects to the mempool.space WebSocket API and routes validated events to Kafka by key:

```mermaid
flowchart TD
    WS["WebSocket<br/>mempool.space"] --> PARSE["JSON Parse"]
    PARSE --> FILTER{"Noise Filter<br/><i>conversions, init,<br/>loadingIndicators</i>"}
    FILTER -->|"Drop"| NULL["∅"]
    FILTER -->|"Pass"| ROUTE{"Route by Key"}

    ROUTE -->|"mempoolInfo"| V1["Validate<br/>MempoolStats"]
    ROUTE -->|"mempool-blocks"| V2["Validate<br/>MempoolBlock[]"]
    ROUTE -->|"block"| SIGNAL["Signal & Fetch"]

    SIGNAL --> FETCH["REST GET<br/>/v1/block/{hash}"]
    FETCH --> V3["Validate<br/>ConfirmedBlock"]

    V1 -->|'key=stats'| KAFKA["Redpanda<br/>mempool-raw"]
    V2 -->|'key=mempool_block'| KAFKA
    V3 -->|'key=confirmed_block'| KAFKA
```

### 3.2 State Consumer (Kafka → PostgreSQL)

The State Consumer materializes Kafka events into PostgreSQL tables based on message key:

```mermaid
flowchart LR
    KAFKA["Redpanda<br/>mempool-raw<br/><i>group: mempool-state-writers</i>"] --> ROUTE{"Key?"}

    ROUTE -->|"stats"| S["MempoolStats<br/>.model_validate_json()"]
    ROUTE -->|"confirmed_block"| B["ConfirmedBlock<br/>.model_validate_json()"]
    ROUTE -->|"mempool_block"| MB["MempoolBlock[]<br/>JSON → Validate"]

    S --> INSERT["INSERT<br/>mempool_snapshots<br/><i>append-only</i>"]
    B --> UPSERT["INSERT ... ON CONFLICT<br/>DO NOTHING<br/>blocks<br/><i>idempotent + pool_name + fee_range</i>"]
    MB --> SNAP["Snapshot Pattern<br/>DELETE + INSERT<br/>mempool_block_projections"]

    INSERT --> PG["PostgreSQL"]
    UPSERT --> PG
    SNAP --> PG
```

### 3.3 API Layer (Read-Only Presentation + Inline Analytics)

```mermaid
flowchart LR
    UI["Next.js<br/>Dashboard"] -->|"HTTP GET"| API["FastAPI<br/>:8000"]

    API --> Q1["/api/mempool/stats"]
    API --> Q2["/api/blocks/recent"]
    API --> Q3["/api/orchestrator/status<br/><i>EMA + Trend (inline)</i>"]
    API --> Q4["/api/watchlist"]

    Q1 -->|"SELECT"| PG["PostgreSQL"]
    Q2 -->|"SELECT"| PG
    Q3 -->|"SELECT + EMA calc"| PG
    Q4 -->|"Stub"| STUB["Empty State<br/><i>Phase 7</i>"]
```

## 4. Component Breakdown

### A. Domain Layer — `src/domain/schemas.py`

Pure Pydantic V2 contracts. Zero imports from databases, Kafka, or frameworks.

| Schema | Purpose | Key Fields |
|---|---|---|
| `MempoolStats` | Mempool state from WS | `mempool_info.size`, `.bytes`, `.total_fee` |
| `MempoolBlock` | Projected block template | `block_size`, `median_fee`, `fee_range` |
| `ConfirmedBlock` | Mined block (Signal & Fetch) | `height`, `id`, `tx_count`, `extras.median_fee`, `extras.pool`, `extras.fee_range` |
| `FeeAdvisory` | RBF/CPFP recommendation | `txid`, `action`, `rbf_fee_sats`, `cpfp_fee_sats` |

**Conventions:**
- All monetary values stored as `int` (Satoshis) — never `float`
- `ConfigDict(strict=True)` enforced on all models
- `alias_generator=to_camel` for automatic API field mapping

### B. Infrastructure — Database (`src/infrastructure/database/`)

| File | Purpose |
|---|---|
| `session.py` | Async SQLAlchemy engine (`asyncpg`, pool_size=5, max_overflow=10) |
| `models.py` | ORM models: `BlockRecord`, `MempoolSnapshot`, `MempoolBlockProjection`, `AdvisoryRecord` |

**PostgreSQL Tables:**

```mermaid
erDiagram
    blocks {
        int height PK
        varchar hash UK
        bigint timestamp
        int tx_count
        int size
        float median_fee
        bigint total_fees
        varchar pool_name "Mining pool name"
        jsonb fee_range "Fee rate distribution"
    }

    mempool_snapshots {
        int id PK
        timestamptz captured_at
        int tx_count
        bigint total_bytes
        bigint total_fee_sats
        float median_fee
    }

    mempool_block_projections {
        int id PK
        timestamptz captured_at
        int block_index "0 = next block"
        int block_size
        float block_v_size "ADR-003"
        int n_tx
        bigint total_fees
        float median_fee
        jsonb fee_range
    }

    advisories {
        int id PK
        varchar txid
        timestamptz created_at
        varchar action
        float current_fee_rate
        float target_fee_rate
        bigint rbf_fee_sats
        bigint cpfp_fee_sats
    }
```

### C. Infrastructure — Messaging (`src/infrastructure/messaging/`)

| File | Purpose |
|---|---|
| `producer.py` | `MempoolProducer` — async aiokafka wrapper with `start()`, `send()`, `stop()` lifecycle |

### D. Workers (`src/workers/`)

| Worker | Role | Input → Output |
|---|---|---|
| `ingestor.py` | Radar | WebSocket → Kafka |
| `state_consumer.py` | Materializer | Kafka → PostgreSQL (stats, blocks, projections) |
| `tx_hunter.py` | Advisory Engine | Kafka → advisories table *(Phase 7)* |

### E. API Layer (`src/api/`)

| File | Purpose |
|---|---|
| `main.py` | FastAPI app, lifespan (DDL bootstrap + dispose), CORS, endpoints |
| `queries.py` | Async SQLAlchemy query functions (read-only) |
| `schemas.py` | Response Pydantic models |

### F. Core (`src/core/`)

| File | Purpose |
|---|---|
| `config.py` | `pydantic-settings` singleton. All env vars centralized. |

### G. Frontend Data Layer (TanStack Query v5)

```mermaid
graph LR
    subgraph "Next.js (Docker :3000)"
        QC["QueryClientProvider"]
        QC --> H1["useMempoolStats<br/><i>poll: 5s</i>"]
        QC --> H2["useRecentBlocks<br/><i>poll: 30s</i>"]
        QC --> H3["useOrchestratorStatus<br/><i>poll: 10s</i>"]
        QC --> H4["useWatchlist<br/><i>poll: 15s</i>"]
    end

    subgraph "FastAPI (:8000)"
        E1["/api/mempool/stats"]
        E2["/api/blocks/recent"]
        E3["/api/orchestrator/status"]
        E4["/api/watchlist"]
    end

    H1 -->|fetchAPI| E1
    H2 -->|fetchAPI| E2
    H3 -->|fetchAPI| E3
    H4 -->|fetchAPI| E4
```

## 5. Infrastructure (Docker Compose)

```mermaid
graph TB
    subgraph "Docker Network"
        RP["Redpanda<br/>:9092 (Kafka)<br/>:8080 (Console)"]
        PG["PostgreSQL 16<br/>:5432<br/><i>mempool DB</i>"]
        PGA["pgAdmin<br/>:5050<br/><i>DB Viewer</i>"]
    end

    subgraph "Host Machine (Local)"
        ING["just radar<br/><i>Ingestor</i>"]
        SC["just state-writer<br/><i>State Consumer</i>"]
        API["just api<br/><i>FastAPI :8000</i>"]
    end

    ING -->|produce| RP
    RP -->|consume| SC
    SC -->|write| PG
    PG -->|read| API
    PGA -->|"browse"| PG
```

## 6. Project Structure

```
backend/
├── src/
│   ├── api/                    # Presentation Layer (FastAPI)
│   │   ├── main.py             # App, lifespan, endpoints
│   │   ├── queries.py          # Async SQLAlchemy queries
│   │   └── schemas.py          # Response models
│   ├── core/                   # Configuration
│   │   └── config.py           # pydantic-settings singleton
│   ├── domain/                 # Domain Layer (Pure)
│   │   └── schemas.py          # Pydantic V2 contracts
│   ├── infrastructure/         # Infrastructure Layer
│   │   ├── database/
│   │   │   ├── session.py      # Async engine + session factory
│   │   │   └── models.py       # ORM models
│   │   └── messaging/
│   │       └── producer.py     # aiokafka async producer
│   └── workers/                # Application Layer
│       ├── ingestor.py         # WS → Kafka (Radar)
│       ├── state_consumer.py   # Kafka → PostgreSQL
│       └── tx_hunter.py        # RBF/CPFP (Phase 7)
├── scripts/
│   ├── backfill_blocks.py      # Maintenance: 144-block initial load
│   └── 01_add_pool_and_projections.sql  # Manual migration
└── tests/
    ├── test_config.py          # 12 tests
    ├── test_schemas.py         # Contract validation
    ├── test_ingestor.py        # Routing logic
    ├── test_kafka_producer.py  # Async producer wrapper
    └── test_state_consumer.py  # ORM models + Snapshot pattern (8 tests)
```

## 7. Architectural Patterns

### Event-Driven Architecture (EDA)
- **Event Broker:** Redpanda (Kafka-compatible, ARM64-native)
- **Topic:** `mempool-raw` — single topic, key-based routing (`stats`, `mempool_block`, `confirmed_block`)
- **Consumer Group:** `mempool-state-writers` — single consumer materializing to PostgreSQL

### Signal & Fetch
- **Signal (WebSocket):** Low-latency stream for mempool state changes
- **Fetch (REST API):** On-demand retrieval for confirmed block data (avoids 1MB Kafka message limit)

### Clean Architecture
- **Dependency Rule:** Domain → ∅ | Infrastructure → Domain + Core | Workers → All | API → Infrastructure + Domain
- **Testability:** Each layer is independently testable with mocked dependencies

### Idempotent Writes
- `BlockRecord`: `INSERT ... ON CONFLICT (height) DO NOTHING`
- `MempoolSnapshot`: Append-only (auto-increment PK)
- `MempoolBlockProjection`: Snapshot pattern (DELETE + INSERT on each event)
- Safe for Kafka consumer replay and backfill re-runs

### Data Validation at Boundary
- All external data validated with Pydantic V2 `strict=True` at ingestion
- Invalid payloads logged and dropped — never corrupt downstream storage
- Monetary values: integer-only (Satoshis) to prevent IEEE 754 precision errors

## 8. Data Governance

> For a detailed breakdown of metric calculations, units, and data lineage, refer to the [Data Dictionary](./data_dictionary.md).