"""FastAPI data layer — reads pre-computed dashboard views from Redis.

The DuckDBConsumer projects data to Redis after each flush.
FastAPI never touches DuckDB files directly.

Usage:
    cd backend && uv run uvicorn src.api.main:app --reload --port 8000
"""

import json
from contextlib import asynccontextmanager

import redis
import httpx
from fastapi import FastAPI, Query, Body, Path as FastAPIPath, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.schemas import (
    MempoolStatsResponse,
    RecentBlocksResponse,
    WatchlistResponse,
    OrchestratorStatusResponse,
)


# =============================================================================
# Redis Client
# =============================================================================

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    """Get or create the Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client


# =============================================================================
# Cache-miss defaults (valid empty-state responses)
# =============================================================================

_EMPTY_MEMPOOL_STATS = {
    "mempool_size": 0, "mempool_bytes": 0, "total_fee_sats": 0,
    "median_fee": 0.0, "blocks_to_clear": 0,
    "delta_size_pct": None, "delta_fee_pct": None,
    "delta_total_fee_pct": None, "delta_blocks_pct": None,
}

_EMPTY_RECENT_BLOCKS = {
    "blocks": [], "latest_height": None,
}

_EMPTY_WATCHLIST = {
    "advisories": [], "stuck_count": 0, "total_count": 0,
}

_EMPTY_ORCHESTRATOR_STATUS = {
    "current_median_fee": 0.0,
    "historical_median_fee": 1.0, "ema_fee": 0.0,
    "ema_trend": "STABLE", "fee_premium_pct": 0.0,
    "traffic_level": "LOW", "latest_block_height": None,
    "patient": {"action": "WAIT", "recommended_fee": 1, "confidence": 0.5},
    "reliable": {"action": "BROADCAST", "recommended_fee": 1, "confidence": 0.8},
}


# =============================================================================
# Helpers
# =============================================================================

def _read_or_default(key: str, default: dict) -> dict:
    """Read a JSON value from Redis, returning default on cache miss."""
    r = _get_redis()
    raw = r.get(key)
    if raw is None:
        return default
    return json.loads(raw)


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Redis client lifecycle."""
    yield
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Mempool Orchestrator API",
    description="Read-only data layer for the Next.js dashboard. Reads from Redis.",
    version="0.3.0",
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
    data = _read_or_default("dashboard:mempool_stats", _EMPTY_MEMPOOL_STATS)
    return MempoolStatsResponse(**data)


@app.get("/api/blocks/recent", response_model=RecentBlocksResponse)
async def get_recent_blocks(
    limit: int = Query(default=10, ge=1, le=50, description="Number of blocks"),
):
    """Confirmed blocks from block_history."""
    data = _read_or_default("dashboard:recent_blocks", _EMPTY_RECENT_BLOCKS)
    # Slice to requested limit (Redis stores up to 10)
    data["blocks"] = data["blocks"][:limit]
    return RecentBlocksResponse(**data)


@app.get("/api/watchlist", response_model=WatchlistResponse)
async def get_watchlist():
    """Tracked transactions with dual RBF/CPFP advisory info."""
    data = _read_or_default("dashboard:watchlist", _EMPTY_WATCHLIST)
    return WatchlistResponse(**data)


@app.post("/api/watchlist", status_code=201)
async def add_to_watchlist(txid: str = Body(..., embed=True, min_length=64, max_length=64)):
    """Add a TXID to the watchlist. DuckDB write — isolated connection."""
    
    # 1. Fetch TX from mempool.space to get original fee and weight
    async with httpx.AsyncClient() as client:
        url = f"{settings.mempool_api_url}/tx/{txid.lower()}"
        resp = await client.get(url, timeout=10)
        
        if resp.status_code == 404:
            raise HTTPException(status_code=400, detail="Transaction not found in mempool")
            
        resp.raise_for_status()
        tx_data = resp.json()
        
    fee = tx_data.get("fee")
    weight = tx_data.get("weight")
    
    if fee is None or weight is None:
        raise HTTPException(status_code=400, detail="Incomplete transaction data from mempool")
        
    # Calculate vsize and fee_rate
    vsize = weight / 4
    fee_rate = fee / vsize

    from src.storage.watchlist import Watchlist, WatchlistEntry
    wl = Watchlist()
    try:
        entry = WatchlistEntry(txid=txid)
        # 2. Save with original fee data so RBF/CPFP can calculate immediately
        added = wl.add_tx(entry, fee=fee, fee_rate=fee_rate)
        return {"added": added, "txid": entry.txid}
    finally:
        wl.close()


@app.delete("/api/watchlist/{txid}")
async def remove_from_watchlist(txid: str = FastAPIPath(..., min_length=64, max_length=64)):
    """Remove a TXID from the watchlist."""
    from src.storage.watchlist import Watchlist
    wl = Watchlist()
    try:
        removed = wl.remove_tx(txid.lower())
        if not removed:
            raise HTTPException(status_code=404, detail="TXID not found in watchlist")
        return {"removed": True, "txid": txid.lower()}
    finally:
        wl.close()


@app.get("/api/orchestrator/status", response_model=OrchestratorStatusResponse)
async def get_orchestrator_status():
    """Dual-strategy engine state: fees, EMA, traffic level, patient + reliable results."""
    data = _read_or_default("dashboard:orchestrator_status", _EMPTY_ORCHESTRATOR_STATUS)
    return OrchestratorStatusResponse(**data)
