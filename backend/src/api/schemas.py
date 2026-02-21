"""Response schemas for the FastAPI data layer.

All models are read-only projections of DuckDB data.
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


# =============================================================================
# /api/mempool/fee-distribution
# =============================================================================

class FeeBand(BaseModel):
    """Single fee band in the histogram."""

    range: str = Field(..., description="Fee range label, e.g. '1-5'")
    count: int = Field(..., description="Estimated tx count in this band")
    pct: float = Field(..., description="Percentage of total")


class FeeDistributionResponse(BaseModel):
    """Fee histogram data from projected mempool blocks."""

    bands: list[FeeBand]
    total_txs: int
    peak_band: str = Field(..., description="Range label with highest percentage")


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

class WatchlistAdvisory(BaseModel):
    """Single tracked transaction with advisory info."""

    txid: str
    role: str = Field(..., description="SENDER or RECEIVER")
    status: str = Field(..., description="PENDING or CONFIRMED")
    current_fee_rate: float | None = Field(None, description="Fee rate (sat/vB)")
    action: str = Field(..., description="Human-readable action, e.g. 'RBF to 22.0 sat/vB'")
    action_type: str = Field(..., description="RBF | CPFP | None")
    cost_sats: int | None = Field(None, description="Estimated cost in satoshis")


class WatchlistResponse(BaseModel):
    """Response for the advisors panel."""

    advisories: list[WatchlistAdvisory]
    stuck_count: int
    total_count: int


# =============================================================================
# /api/orchestrator/status
# =============================================================================

class OrchestratorStatusResponse(BaseModel):
    """Strategy engine state for header and status bar."""

    strategy_mode: str = Field(..., description="PATIENT or RELIABLE")
    current_median_fee: float
    historical_median_fee: float
    ema_fee: float
    ema_trend: str = Field(..., description="RISING | FALLING | STABLE")
    fee_premium_pct: float
    traffic_level: str = Field(..., description="LOW | NORMAL | HIGH")
    latest_block_height: int | None = None
