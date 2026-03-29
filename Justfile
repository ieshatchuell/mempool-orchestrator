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
# DOCKER CLUSTER LIFECYCLE
# ==========================================

# Start the entire microservices stack (detached)
up:
    @echo "{{green}}🚀 Starting the Mempool Orchestrator Cluster...{{reset}}"
    docker compose up --build -d
    @echo "{{green}}✅ Cluster is initializing (check health with just status).{{reset}}"

# Stop the entire microservices stack
down:
    @echo "{{green}}🛑 Stopping all services...{{reset}}"
    docker compose down
    @echo "{{green}}💤 Cluster stopped.{{reset}}"

# View running containers status
status:
    @echo "{{green}}🔍 Checking Docker Cluster Status...{{reset}}"
    @docker compose ps

# Tail logs from a specific service (e.g. just logs frontend, just logs worker-tx-hunter)
logs service:
    @echo "{{green}}📝 Tailing logs for {{service}}...{{reset}}"
    docker compose logs -f {{service}}

# Restart a specific service
restart service:
    @echo "{{green}}🔄 Restarting {{service}}...{{reset}}"
    docker compose restart {{service}}

# ==========================================
# TESTING & MAINTENANCE
# ==========================================

# Run backend test suite inside the container
test:
    @echo "{{green}}🧪 Running Backend Tests in FastAPI container...{{reset}}"
    docker compose exec fastapi uv run pytest -v

# Open pgAdmin database viewer (PostgreSQL GUI)
db-viewer:
    @echo "{{green}}🗄️  pgAdmin Database Viewer{{reset}}"
    @echo "──────────────────────────────────────"
    @echo "pgAdmin URL:  http://localhost:5050"
    @echo "Credentials:  see .env (PGADMIN_* and POSTGRES_*)"
    @echo "──────────────────────────────────────"
    @open http://localhost:5050