"""FastAPI data layer — read-only presentation layer for the mempool dashboard.

Reads from PostgreSQL via SQLAlchemy async sessions.
All endpoints are read-only except watchlist mutations (deferred).

Usage:
    cd backend && uv run uvicorn src.api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Body, Path as FastAPIPath, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.infrastructure.database.session import engine
from src.infrastructure.database.models import Base
from src.api.queries import (
    query_mempool_stats,
    query_recent_blocks,
    query_watchlist_advisories,
    query_orchestrator_status,
)
from src.api.schemas import (
    MempoolStatsResponse,
    RecentBlocksResponse,
    WatchlistResponse,
    OrchestratorStatusResponse,
)


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage DB engine lifecycle — DDL bootstrap + clean dispose."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("API DDL bootstrap complete — tables ready.")
    yield
    await engine.dispose()
    logger.info("API DB engine disposed.")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Mempool Orchestrator API",
    description="Read-only data layer for the Next.js dashboard. Reads from PostgreSQL.",
    version="0.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/api/mempool/stats", response_model=MempoolStatsResponse)
async def get_mempool_stats():
    """KPI card data: mempool size, fees, blocks to clear, 1h deltas."""
    data = await query_mempool_stats()
    return MempoolStatsResponse(**data)


@app.get("/api/blocks/recent", response_model=RecentBlocksResponse)
async def get_recent_blocks(
    limit: int = Query(default=10, ge=1, le=50, description="Number of blocks"),
):
    """Confirmed blocks table."""
    data = await query_recent_blocks(limit=limit)
    return RecentBlocksResponse(**data)


@app.get("/api/watchlist", response_model=WatchlistResponse)
async def get_watchlist():
    """Tracked transactions with dual RBF/CPFP advisory info."""
    data = await query_watchlist_advisories()
    return WatchlistResponse(**data)


@app.post("/api/watchlist", status_code=201)
async def add_to_watchlist(txid: str = Body(..., embed=True, min_length=64, max_length=64)):
    """Add a TXID to the watchlist."""
    # Deferred — advisory pipeline pending
    raise HTTPException(status_code=501, detail="Not implemented — pending advisory phase")


@app.delete("/api/watchlist/{txid}")
async def remove_from_watchlist(txid: str = FastAPIPath(..., min_length=64, max_length=64)):
    """Remove a TXID from the watchlist."""
    # Deferred — advisory pipeline pending
    raise HTTPException(status_code=501, detail="Not implemented — pending advisory phase")


@app.get("/api/orchestrator/status", response_model=OrchestratorStatusResponse)
async def get_orchestrator_status():
    """Market metrics: fees, EMA, traffic level, strategy data (pure SQL/Python)."""
    data = await query_orchestrator_status()
    return OrchestratorStatusResponse(**data)
