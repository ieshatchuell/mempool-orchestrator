"""Response schemas for the FastAPI data layer.

All models are read-only projections of PostgreSQL data.
Monetary values follow project convention: stored as int (Satoshis),
displayed with explicit formatting fields when BTC output is needed.
"""

from pydantic import BaseModel, Field


# =============================================================================
# /api/mempool/stats
# =============================================================================

class MempoolStatsResponse(BaseModel):
    """KPI card data — current mempool snapshot."""

    mempool_size: int = Field(..., description="Transaction count in mempool")
    mempool_bytes: int = Field(..., description="Total mempool size in bytes")
    total_fee_sats: int = Field(..., description="Total fees in satoshis")
    median_fee: float = Field(..., description="Next-block median fee rate (sat/vB)")
    blocks_to_clear: int = Field(..., description="Projected blocks needed to clear mempool")
    delta_size_pct: float | None = Field(None, description="Mempool size change vs 1h ago (%)")
    delta_fee_pct: float | None = Field(None, description="Median fee change vs 1h ago (%)")
    delta_total_fee_pct: float | None = Field(None, description="Total fees change vs 1h ago (%)")
    delta_blocks_pct: float | None = Field(None, description="Blocks to clear change vs 1h ago (%)")


# =============================================================================
# /api/blocks/recent
# =============================================================================

class RecentBlock(BaseModel):
    """Confirmed block from block_history table."""

    height: int
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    tx_count: int
    size_bytes: int
    median_fee: float = Field(..., description="Median fee rate (sat/vB)")
    total_fees_sats: int = Field(..., description="Total fees in satoshis")
    fee_range: list[float] = Field(default_factory=list, description="[min, p10, p25, p50, p75, p90, max]")
    pool_name: str | None = None


class RecentBlocksResponse(BaseModel):
    """Response for the blocks table."""

    blocks: list[RecentBlock]
    latest_height: int | None = None


# =============================================================================
# /api/watchlist
# =============================================================================

class AdvisorAction(BaseModel):
    """Single advisor recommendation (RBF or CPFP)."""

    action: str = Field(..., description="Human-readable recommendation")
    cost_sats: int | None = Field(None, description="Estimated cost in satoshis")


class WatchlistAdvisory(BaseModel):
    """Tracked tx with dual advisor info (no role required)."""

    txid: str
    status: str = Field(..., description="Pending | Stuck | Confirmed")
    current_fee_rate: float | None = None
    rbf: AdvisorAction | None = Field(None, description="Sender path: RBF advice")
    cpfp: AdvisorAction | None = Field(None, description="Receiver path: CPFP advice")


class WatchlistResponse(BaseModel):
    """Response for the advisors panel."""

    advisories: list[WatchlistAdvisory]
    stuck_count: int
    total_count: int


# =============================================================================
# /api/orchestrator/status
# =============================================================================

class StrategyResult(BaseModel):
    """Result of applying a single strategy to current market data."""

    action: str = Field(..., description="BROADCAST or WAIT")
    recommended_fee: int = Field(..., description="Recommended fee rate (sat/vB)")
    confidence: float = Field(..., description="Decision confidence 0.0-1.0")


class OrchestratorStatusResponse(BaseModel):
    """Dual-strategy engine state for header and status bar."""

    current_median_fee: float
    historical_median_fee: float
    ema_fee: float
    ema_trend: str = Field(..., description="RISING | FALLING | STABLE")
    fee_premium_pct: float
    traffic_level: str = Field(..., description="LOW | NORMAL | HIGH")
    latest_block_height: int | None = None
    patient: StrategyResult
    reliable: StrategyResult

