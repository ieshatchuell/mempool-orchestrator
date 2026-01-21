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

### 2026-01-21 | Configuration Hardening & Modern Refactoring
**Status:** COMPLETED

**Objective:** Eliminate configuration hardcoding, enhance type safety, and adopt modern Python 3.12 idioms for message processing.

**Actions:**
1.  **Configuration Management:**
    * Implemented **Pydantic Settings** (`src/config.py`) to enforce strict type validation on environment variables.
    * Centralized configuration in a `.env` file (git-ignored) to secure sensitive credentials (WS URLs, Broker addresses).
    * Added whitespace sanitization validators to prevent "silent failures" from copy-paste errors.
2.  **Code Modernization (Python 3.12):**
    * Refactored `src/ingestors/mempool_ws.py` to replace imperative `if/else` chains with **Structural Pattern Matching** (`match/case`).
    * Implemented a robust WebSocket handshake protocol (`action: init` + `action: want`) to ensure stable data streaming from Mempool.space API v1.
3.  **Repository Standards:**
    * Established a **Feature Branch Workflow** (GitHub Flow) with SSH authentication.
    * Refined `.gitignore` to strictly exclude `.env` and `.duckdb` files.

**Outcome:**
The system is now environment-agnostic. It validates configuration at startup (fail-fast) and routes events using declarative logic.

