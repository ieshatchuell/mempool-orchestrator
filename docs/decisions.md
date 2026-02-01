# Project Journal: Mempool Orchestrator

## Phase 1: Infrastructure Foundation (Q1 2026)

### 2026-01-18 | E2E Ingestion Pipeline & Infrastructure Hardening
**Status:** COMPLETED

**Objective:** Establish a high-performance, event-driven backbone to capture real-time Bitcoin mempool data and ensure architectural parity between local development and production-ready systems.

**Actions:**
1.  **Environment Setup:**
    * Provisioned a surgical development environment on **macOS M4** using **OrbStack** for container management and **uv** for Python dependency resolution.
    * Enforced **Python 3.12** across the stack to leverage `asyncio` performance gains and modern type hinting.
2.  **Infrastructure Deployment:**
    * Deployed a **Redpanda** broker via Docker Compose. Selected for its native ARM64 efficiency and JVM-free architecture, minimizing resource overhead on the M4 silicon.
    * Initialized the `mempool-raw` topic with `acks=1` for balanced durability.
3.  **Application Layer - Ingestor Engine:**
    * **Core Logic:** Implemented a modular package structure under `src/`.
    * **`src/common/kafka_producer.py`**: Engineered a high-level producer wrapper using `confluent-kafka`. Optimized with non-blocking `poll(0)` calls to handle delivery reports without saturating the event loop.
    * **`src/ingestors/mempool_ws.py`**: Developed an asynchronous WebSocket client for `mempool.space`. Implemented the specific subscription protocol (`want-stats`, `track-mempool`) to stream live transaction batches.
4.  **E2E Pipeline Validation:**
    * Successfully streamed live mempool data from external WebSockets into the local Redpanda bus.
    * Verified data persistence and JSON integrity via `rpk topic consume`, confirming successful offsets and key-value delivery.

**Technical Deep Dive: Infrastructure Verification**
To audit the broker's health and ensure a stable backbone, we utilized the following baseline command:
`docker exec -it infra-redpanda-1 rpk cluster health`

**Technical Challenges & Resolutions:**
- **Module Resolution:** Addressed `ModuleNotFoundError` by transitioning from direct script execution to **Module Execution Mode** (`python -m src.ingestors.mempool_ws`). Added `__init__.py` markers to formalize the package namespace.
- **Dependency Synchronization:** Resolved a `uv.lock` version drift by executing a full `uv sync` after manual `pyproject.toml` updates, ensuring a deterministic build environment.
- **Connectivity Handling:** Identified `Connection refused` errors caused by inactive containers. Implemented a pre-runtime network probe routine (`nc -zv`) for broker availability.

---

### 2026-01-20 | Developer Experience (DX) & Workflow Standardization
**Status:** COMPLETED

**Objective:** Abstract complex execution logic into a unified command runner to ensure reproducibility, reduce cognitive load, and standardize the "Developer Loop".

**Actions:**
1.  **Task Runner Integration:**
    * Adopted **Just** as the project's standard command runner.
    * Created a `Justfile` at the project root to encapsulate infrastructure lifecycle (`infra-up`, `infra-down`) and application execution.
2.  **Execution Abstraction:**
    * Replaced verbose shell commands (e.g., `uv run python -m ...` or `docker compose ...`) with semantic recipes.
    * Implemented a `check` recipe for instant system health verification, validating Python environment versions and Docker connectivity in a single pass.
3.  **Documentation Alignment:**
    * Refactored `README.md` and `architecture.md` to establish `just` commands as the canonical entry point for the project.

**Project Snapshot (End of Day):**
```text
.
├── Justfile            # Command definitions
├── docs/               # Updated architecture & journal
├── infra/
│   └── docker-compose.yml
├── src/
│   ├── common/         # Infrastructure clients
│   └── ingestors/      # Data source connectors
├── pyproject.toml
└── README.md
```

### 2026-01-21 | Configuration Hardening & Modern Refactoring
**Status:** COMPLETED

**Objective:** Eliminate configuration hardcoding, enhance type safety, and adopt modern Python 3.12 idioms for message processing.

**Actions:**
1.  **Configuration Management:**
    * Implemented **Pydantic Settings** (`src/config.py`) for strict type validation.
    * Centralized variables in `.env` (git-ignored) for security and portability.
    * Added `@field_validator` for automated whitespace sanitization.
2.  **Code Modernization (Python 3.12):**
    * Refactored `src/ingestors/mempool_ws.py` using **Structural Pattern Matching** (`match/case`) for event routing.
    * Optimized the WebSocket handshake (`action: init` + `action: want`) to align with API v1 standards.
3.  **Repository Standards:**
    * Established **GitHub Flow** with SSH authentication.
    * Hardened `.gitignore` against accidental leaks of `.env` or `.duckdb` files.

**Outcome:**
System is now environment-agnostic, fail-fast on misconfiguration, and utilizes declarative routing logic.

### 2026-01-25 | Storage Layer & Medallion Architecture
**Status:** COMPLETED

**Objective:** Persist real-time mempool data into a local OLAP storage and implement the first analytical layer.

**Actions:**
1.  **Persistence:** Integrated **DuckDB** with a buffered consumer (`src/storage/duckdb_consumer.py`) using `batch_size=50`.
2.  **Reliability:** Implemented signal handling (`_cleanup`) to ensure clean file lock releases on exit.
3.  **Data Modeling (Bronze -> Silver):**
    * **Bronze:** Raw JSON storage in `raw_mempool`.
    * **Silver:** Created `v_mempool_stats` view.
    * **Fix:** Corrected `total_fee_btc` unit handling (detected field already in BTC) and added `avg_tx_fee_sats` for operational analysis.
4.  **Dependencies:** Added `pandas` and `numpy` via `uv add` for terminal-based data auditing.

**Outcome:**
Validated end-to-end pipeline. The system now provides structured, unit-corrected Bitcoin network metrics via SQL.

# Engineering Journal

## [2026-01-27] Architecture Pivot: From Streaming to Hybrid Signal & Fetch

### Context
Attempts to implement the "Silver Layer" (raw transactions ingestion) on branch `feat/silver-transactions` exposed fundamental infrastructure limitations.

### Blockers Identified (Root Cause Analysis)
1.  **Kafka Message Size:** Bitcoin blocks (via `track-mempool`) are ~2-4MB. Redpanda defaults to 1MB limits. Increasing this causes network instability (Head-of-Line Blocking).
2.  **Mempool Protocol Conflicts:** The WebSocket API drops the connection or ignores commands when mixing lightweight subscriptions (`want: ['stats']`) with heavyweight ones (`track-mempool`).
3.  **Data Completeness:** The public WebSocket feed filters out transaction details (missing `vin`/`vout`) to save bandwidth.

### Decisions & Architecture Pivot
* **Discard Pure Streaming for Transactions:** WebSocket is insufficient for data engineering needs on the Silver Layer.
* **Adopt "Hybrid Signal & Fetch" Pattern:**
    * **Signal (WebSocket):** Listens for `block` events and `stats`. Low bandwidth.
    * **Fetch (REST API):** Triggered by the signal. Performs a robust `GET /block/{hash}/txs`.
    * **Chunking Strategy:** The Application Layer splits the 4MB payload into micro-batches (e.g., 200 txs) before producing to Kafka, bypassing the 1MB limit without ops changes.

### Capacity Planning
* **Historical Data:** ~2.3 Billion transactions total.
* **Storage Strategy:** DuckDB native columnar storage (estimated ~350GB compressed).
* **Backfill:** We will implement a "Lookback Strategy" (fetch last N blocks on boot) instead of a full historical sync for the MVP.

---

## ADR-002: Strict Data Contracts & Infrastructure Testing
**Date:** 2026-01-29  
**Status:** ✅ IMPLEMENTED  
**Context:** Phase 2 - Data Quality & Reliability

### Problem Statement
As the system grew, relying on raw JSON and untested infrastructure components introduced risks:

1. **Type Safety:** No guarantee that fees were integers or required fields existed.
2. **Logic Fragility:** Routing logic and noise filtering in the ingestor were untested.
3. **Infra Blind Spots:** The Kafka Producer wrapper and Configuration loading had no unit tests, making refactors dangerous.

### Decision
1. **Adopt Pydantic v2 Strict Mode:** Enforce data contracts at the ingestion boundary.
2. **Implement "Radar" Ingestion:** Explicitly route and validate specific WebSocket events (`stats`, `blocks`), filtering out noise (`conversions`).
3. **Enforce Comprehensive Unit Testing:** Mandate tests for both logic (Schemas, Ingestor) and infrastructure (Producer, Config) using Mocks.

### Implementation
#### Data Contracts (`src/schemas.py`)
- Pydantic v2 models with `strict=True`
- Automatic camelCase ↔ snake_case mapping
- Monetary values enforced as `int` (Satoshis)
- Models: `MempoolStats`, `MempoolBlock`, `Transaction`

#### Radar Ingestion (`src/ingestors/mempool_ws.py`)
- Silent filter for `conversions` noise
- Event routing: `mempoolInfo` → stats, `mempool-blocks` → mempool_block
- Fail-fast validation with Pydantic

#### Testing Coverage (42 Unit Tests)
```bash
tests/test_schemas.py         # 9 tests  - Contract validation
tests/test_ingestor.py        # 9 tests  - Routing logic
tests/test_kafka_producer.py  # 12 tests - Infrastructure wrapper
tests/test_config.py          # 12 tests - Environment validation
```

**Test Strategy:**
- Mocked infrastructure (no Docker required)
- Isolated unit tests for each component
- Happy path + error handling coverage

### Consequences

**Positive:**
1. **Confidence:** 42+ unit tests ensure core components work in isolation without needing Docker.
2. **Data Integrity:** Invalid data is rejected before hitting Kafka.
3. **Maintainability:** Snake_case conversion is handled automatically by the Schema layer.

**Trade-offs:**
1. **Dev Time:** Writing tests and mocks requires upfront investment (paid off by stability).
2. **Strictness:** API changes (e.g., new fields) require explicit schema updates.

**Test Results:**
```
======================== 42 passed in 0.12s =========================
```

### Next Steps
1. ✅ Schema validation for stats and mempool-blocks
2. ✅ Infrastructure testing (Config, Producer)
3. ✅ Refactor DuckDB consumer to use Pydantic schemas
4. ⏳ REST API integration for full transaction fetch

---

### 2026-02-01 | Storage Layer Refactor (The Vault)
**Status:** COMPLETED

**Objective:** Transition from raw JSON storage to a strongly-typed, analytical schema in DuckDB to enable immediate SQL analysis.

**Actions:**

1. **Refactor:** Updated `src/storage/duckdb_consumer.py` to utilize `src/schemas.py` for data parsing.

2. **Schema Evolution:** Replaced `raw_mempool` with two structured tables:
   - `mempool_stats`: Stores network pulse (fees in Satoshis).
   - `projected_blocks`: Stores candidate block templates.

3. **Semantic Fix:** Corrected the mapping of `min_fee` (previously misidentified as median) and enforced `UBIGINT` for all monetary values.

**Outcome:** The pipeline now ingests, validates, and stores typed data End-to-End. Data is query-ready immediately upon insertion.
---

## Phase 2: Infrastructure Maturity & Observability (Q1 2026)

### 2026-02-01 | REST API Client & Analytics Dashboard
**Status:** COMPLETED

**Objective:** Implement a hybrid ingestion strategy (Signal + Fetch) and add real-time observability through an analytics dashboard.

**Actions:**

1. **REST API Client Implementation:**
   - Created `src/ingestors/mempool_api.py` with async `httpx.AsyncClient`.
   - Implemented `get_block_stats(block_hash: str)` for on-demand block data fetching.
   - Added custom `MempoolAPIError` exception for comprehensive error handling (HTTP 4xx/5xx, network errors, JSON parsing).
   - Configuration: Base URL managed via `settings.mempool_api_url` (strict, no hardcoding).
   - Testing: 13 new tests using `respx` mocking (success, failure, network errors, integration scenarios).

2. **Analytics Dashboard:**
   - Created `dashboard.py` using Streamlit framework.
   - Read-only DuckDB connection for real-time data visualization.
   - Added `just dashboard` command to Justfile for one-command launch.
   - Features: Mempool statistics, projected blocks, historical trends, data quality monitoring.

3. **Architecture Evolution:**
   - Migrated to **Hybrid Signal & Fetch** pattern:
     - **Signal (WebSocket):** Low-latency mempool state changes (Radar).
     - **Fetch (REST API):** On-demand confirmed block data (Fetcher).
   - Rationale: Avoids Kafka message size limits (1MB) and ensures data completeness.

4. **Configuration Management:**
   - Added `mempool_api_url` field to `src/config.py` with default `https://mempool.space/api`.
   - All configuration fields validated with Pydantic and whitespace-stripped.

5. **Documentation Overhaul:**
   - Updated `README.md`: Removed broken links, documented typed schemas, added hybrid architecture notes.
   - Updated `docs/architecture.md`: Added sections for Fetcher (C) and Dashboard (D), upgraded data flow to V4.
   - Updated `docs/decisions.md`: Added this Phase 2 milestone entry.

**Test Results:**
```
======================== 55 passed in 0.12s =========================
Previous: 42 tests
New: 13 tests (REST API client)
```

**Outcome:** The system now supports both real-time streaming (WebSocket) and on-demand fetching (REST API) with unified observability through the dashboard. Infrastructure is production-ready for block backfill and auditing workflows.

### Next Steps
1. ✅ Schema validation for stats and mempool-blocks
2. ✅ Infrastructure testing (Config, Producer)
3. ✅ Refactor DuckDB consumer to use Pydantic schemas
4. ✅ REST API integration for block data fetching
5. ✅ Analytics dashboard for real-time observability
6. ⏳ Implement `get_block_transactions()` for full transaction ingestion
7. ⏳ Add retry logic with exponential backoff to REST client
8. ⏳ Block backfill strategy for historical data
