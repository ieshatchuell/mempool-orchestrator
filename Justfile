# ==========================================
# CONFIGURATION
# ==========================================

# Load .env file automatically if it exists
set dotenv-load

# Use zsh to ensure compatibility with macOS ecosystem
set shell := ["zsh", "-c"]

# UX: Define colors for output messages
green := `tput setaf 2`
red := `tput setaf 1`
reset := `tput sgr0`

# ==========================================
# DEFAULT ACTION
# ==========================================

# List all available recipes
default:
    @just --list

# ==========================================
# INFRASTRUCTURE (Docker / Redpanda)
# ==========================================

# Start the infrastructure stack in detached mode
infra-up:
    @echo "{{green}}🚀 Starting Redpanda infrastructure...{{reset}}"
    cd infra && docker compose up -d
    @echo "{{green}}✅ Infrastructure is ready.{{reset}}"

# Stop the infrastructure stack
infra-down:
    @echo "{{green}}🛑 Stopping services...{{reset}}"
    cd infra && docker compose down
    @echo "{{green}}💤 Infrastructure stopped.{{reset}}"

# View running containers status
# FIX: We use '{{{{' to escape Docker's Go-Template syntax so 'just' ignores it
infra-status:
    @echo "{{green}}🔍 Checking Docker containers...{{reset}}"
    @docker ps --format "table {{{{.Names}}}}\t{{{{.Status}}}}\t{{{{.Ports}}}}"

# Tail logs from Redpanda
infra-logs:
    cd infra && docker compose logs -f

# ==========================================
# DATA PIPELINE (Backend / UV)
# ==========================================

# Run the Mempool WebSocket Ingestor (The "Radar")
radar:
    @echo "{{green}}📡 Launching Mempool Ingestor (Topic: mempool-raw)...{{reset}}"
    cd backend && uv run python -m src.ingestors.mempool_ws

# Run the DuckDB Storage Consumer
storage:
    @echo "📦 Starting DuckDB Storage Consumer..."
    cd backend && uv run python -m src.storage.duckdb_consumer

# Run orchestrator locally (for development)
orchestrator:
    @echo "{{green}}🧠 Running AI Orchestrator locally...{{reset}}"
    cd backend && uv run python -m src.orchestrator.main

# ==========================================
# FRONTEND (Next.js via Docker)
# ==========================================

# Launch the analytics dashboard (ephemeral Docker container)
dashboard:
    @echo "{{green}}🚀 Launching Mempool Dashboard (Docker)...{{reset}}"
    @sh -c "sleep 4 && open http://localhost:3000" &
    docker run --rm -it \
        -v {{justfile_directory()}}/frontend:/app \
        -w /app \
        -p 3000:3000 \
        node:20-alpine \
        sh -c "npm install && npm run dev -- -H 0.0.0.0"

# ==========================================
# TESTING
# ==========================================

# Run backend test suite
test:
    @echo "{{green}}🧪 Running Backend Tests...{{reset}}"
    cd backend && uv run pytest -v

# ==========================================
# MAINTENANCE & UTILS
# ==========================================

# Run a full system health check (Python env + Docker connectivity)
check:
    @echo "{{green}}🛠️  Performing System Health Check...{{reset}}"
    @echo "\n[1/2] Backend Python Environment (via UV):"
    @cd backend && uv run python --version
    @echo "\n[2/2] Infra Status:"
    @cd infra && docker compose ps

# Sync backend dependencies (frontend deps managed via Docker)
sync:
    @echo "{{green}}📦 Syncing Backend dependencies...{{reset}}"
    cd backend && uv sync
    @echo "{{green}}✅ Backend dependencies synced.{{reset}}"

# Debug the DuckDB database
debug-db:
    @echo "🔍 Running DB Debug Script..."
    uv run python scripts/debug_db.py

# ==========================================
# AI ORCHESTRATOR (Phase 2)
# ==========================================

# Start AI infrastructure (Ollama + Orchestrator)
ai-up:
    @echo "{{green}}🧠 Starting AI Infrastructure...{{reset}}"
    cd infra && docker compose up -d ollama orchestrator
    @echo "{{green}}✅ AI services started.{{reset}}"

# Stop AI infrastructure
ai-down:
    @echo "{{green}}🧠 Stopping AI Infrastructure...{{reset}}"
    cd infra && docker compose stop ollama orchestrator
    @echo "{{green}}💤 AI services stopped.{{reset}}"

# View orchestrator logs
ai-logs:
    docker logs -f orchestrator