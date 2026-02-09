# === Build Stage ===
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Sync dependencies (no dev deps for production)
RUN uv sync --frozen --no-dev

# === Runtime Stage ===
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ ./src/
COPY pyproject.toml uv.lock ./

# Set environment for uv
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

CMD ["uv", "run", "python", "-m", "src.orchestrator.main"]
