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
# INFRASTRUCTURE (Docker: Redpanda + PostgreSQL)
# ==========================================

# Start the infrastructure stack in detached mode
infra-up:
    @echo "{{green}}🚀 Starting infrastructure (Redpanda, PostgreSQL)...{{reset}}"
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

# Tail logs from infrastructure
infra-logs:
    cd infra && docker compose logs -f

# ==========================================
# DATA PIPELINE (Backend / UV)
# ==========================================

# Run the Mempool WebSocket Ingestor (The "Radar")
radar:
    @echo "{{green}}📡 Launching Mempool Ingestor (Topic: mempool-raw)...{{reset}}"
    cd backend && uv run python -m src.workers.ingestor

# Run the State Consumer (Kafka → PostgreSQL materializer)
state-writer:
    @echo "{{green}}📦 Starting State Consumer (Kafka → PostgreSQL)...{{reset}}"
    cd backend && uv run python -m src.workers.state_consumer

# Incremental backfill — fills only missing blocks (non-destructive)
backfill:
    @echo "{{green}}📥 Incremental backfill (gap detection)...{{reset}}"
    cd backend && uv run python -m src.workers.backfill

# Full backfill — DEPRECATED, kept for migration purposes only
backfill-legacy:
    @echo "{{red}}⚠️  Legacy backfill (destructive flush + re-insert)...{{reset}}"
    cd backend && uv run python -m scripts.backfill_blocks

# Run the Advisory Engine (tx_hunter — RBF/CPFP scanner)
hunter:
    @echo "{{green}}🕵️ Launching Advisory Engine (poll: 60s)...{{reset}}"
    cd backend && uv run python -m src.workers.tx_hunter

# ==========================================
# API SERVER (FastAPI)
# ==========================================

# Start the FastAPI data layer on port 8000
api:
    @echo "{{green}}🔌 Starting FastAPI API server (port 8000)...{{reset}}"
    cd backend && uv run uvicorn src.api.main:app --reload --port 8000

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

# Open pgAdmin database viewer (PostgreSQL GUI)
db-viewer:
    @echo "{{green}}🗄️  pgAdmin Database Viewer{{reset}}"
    @echo "──────────────────────────────────────"
    @echo "pgAdmin URL:  http://localhost:5050"
    @echo "Credentials:  see .env (PGADMIN_* and POSTGRES_*)"
    @echo "──────────────────────────────────────"
    @open http://localhost:5050