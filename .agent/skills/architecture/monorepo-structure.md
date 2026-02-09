---
name: monorepo-structure-enforcement
description: Enforces the separation of concerns between Data Backend, Frontend UI, and Infrastructure.
patterns: ["**/*"]
---

# Project Structure Standards (Monorepo)

## 1. Directory Layout Rules
This project follows a strict "Decoupled Monorepo" pattern. You MUST respect these boundaries:

- **`backend/`**: The "Brain". Pure Data Engineering (Python).
    - Contains: `src/` (Ingestors, Orchestrator, Storage), `tests/`.
    - Dependencies: `pandas`, `duckdb`, `kafka`, `pydantic`.
    - **FORBIDDEN:** Streamlit, UI code, plotting libraries (except for static generation).
- **`frontend/`**: The "Face". User Interface.
    - Contains: `app/` (Streamlit source).
    - Dependencies: `streamlit`, `plotly`, `requests`/`duckdb` (reading only).
- **`data/`**: State storage.
    - Contains: `.duckdb` files.
    - **Constraint:** Git-ignored. Never commit binary data.
- **`infra/`**: Infrastructure as Code.
    - Contains: `docker-compose.yml`, Dockerfiles.

## 2. Import Rules
- Backend code CANNOT import Frontend code.
- Frontend code imports Backend modules ONLY if installed as a library or via strict path mapping.
- Prefer decoupled communication (Database, API) over direct imports where possible.

## 3. Configuration
- `.env` stays at the **ROOT**.
- `Justfile` stays at the **ROOT** and orchestrates sub-commands (e.g., `cd backend && uv run...`).