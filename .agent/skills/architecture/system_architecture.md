---
name: system-architecture-enforcement
description: Enforces strict separation of concerns for the Event-Driven System (Redpanda + PostgreSQL + Next.js).
patterns: ["**/*"]
---

# Project Structure Standards (Event-Driven Architecture)

## 1. Directory Layout Rules
This project follows a decoupled architecture. You MUST respect these boundaries:

- **`backend/`**: Pure Data Engineering & API (Python).
    - **`src/api/`**: FastAPI routes. (Presentation layer).
    - **`src/core/`**: Configuration (`pydantic-settings`), logging. Single source of truth for env vars.
    - **`src/domain/`**: Pydantic V2 schemas (Transaction, Block, Rules). ZERO external dependencies (no DB/Kafka imports).
    - **`src/infrastructure/`**: Database models (`sqlalchemy` + `asyncpg`) and Message Brokers (`aiokafka`).
    - **`src/workers/`**: Async event loops (e.g., `ingestor.py`, `tx_hunter.py`).
    - **FORBIDDEN:** DuckDB, Ollama, AI Agents, Streamlit, Pandas. No files outside these specific directories.

- **`frontend/`**: The User Interface.
    - Next.js App Router (`app/`, `components/`, `hooks/`).
    - Constraints: Read-only via FastAPI. No direct DB connections.

- **`infra/`**: Infrastructure as Code.
    - `docker-compose.yml` (Redpanda, PostgreSQL, Backend, Frontend).

## 2. Strict Configuration Rules
- NO MAGIC STRINGS. NO HARDCODED URLS OR PORTS.
- All configuration must be loaded from `/.env` via `backend/src/core/config.py` using `pydantic-settings`.
- Execution commands MUST be encapsulated in the root `Justfile`.

## 3. Environment & Dependency Isolation (Zero Global Installs)
- NEVER install dependencies or packages globally on the host machine.
- **Backend:** Dependencies MUST be managed exclusively via `uv` (in `pyproject.toml` / `uv.lock`). All Python execution must happen within the `uv` managed virtual environment.
- **Infrastructure:** All external services (PostgreSQL, Redpanda, etc.) MUST run inside Docker containers via `docker-compose.yml`.