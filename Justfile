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
# DATA PIPELINE (Python / UV)
# ==========================================

# Run the Mempool WebSocket Ingestor (The "Radar")
radar:
    @echo "{{green}}📡 Launching Mempool Ingestor (Topic: mempool-raw)...{{reset}}"
    @# We use 'uv run' to ensure the correct Python 3.12 virtual environment is used
    uv run python -m src.ingestors.mempool_ws

# ==========================================
# MAINTENANCE & UTILS
# ==========================================

# Run a full system health check (Python env + Docker connectivity)
check:
    @echo "{{green}}🛠️  Performing System Health Check...{{reset}}"
    @echo "\n[1/2] Python Environment (via UV):"
    @uv run python --version
    @echo "\n[2/2] Infra Status:"
    @cd infra && docker compose ps

# Sync project dependencies from pyproject.toml
sync:
    @echo "{{green}}📦 Syncing dependencies...{{reset}}"
    uv sync

# Run the DuckDB Storage Consumer
storage:
    @echo "📦 Starting DuckDB Storage Consumer..."
    uv run python -m src.storage.duckdb_consumer

# Launch the analytics dashboard
dashboard:
    @echo "🚀 Launching Mempool Dashboard..."
    @uv run --with streamlit streamlit run dashboard.py

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

# Run orchestrator locally (for development)
orchestrator:
    @echo "{{green}}🧠 Running AI Orchestrator locally...{{reset}}"
    uv run python -m src.orchestrator.main

# View orchestrator logs
ai-logs:
    docker logs -f orchestrator