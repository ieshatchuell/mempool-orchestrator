"""Async query functions for the FastAPI data layer.

All functions use SQLAlchemy async sessions to read from PostgreSQL.
No framework imports — fully testable in isolation.
Read-only: no INSERT/UPDATE/DELETE operations.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc

from src.infrastructure.database.session import async_session
from src.infrastructure.database.models import BlockRecord, MempoolSnapshot


# =============================================================================
# MEMPOOL STATS (KPI Cards)
# =============================================================================

async def query_mempool_stats() -> dict:
    """Query latest mempool snapshot + 1h-ago snapshot for deltas.

    Returns:
        Dict matching MempoolStatsResponse fields.
    """
    async with async_session() as session:
        # Latest snapshot
        latest_stmt = (
            select(MempoolSnapshot)
            .order_by(desc(MempoolSnapshot.captured_at))
            .limit(1)
        )
        latest = (await session.execute(latest_stmt)).scalar_one_or_none()

        if not latest:
            return {
                "mempool_size": 0,
                "mempool_bytes": 0,
                "total_fee_sats": 0,
                "median_fee": 0.0,
                "blocks_to_clear": 0,
                "delta_size_pct": None,
                "delta_fee_pct": None,
                "delta_total_fee_pct": None,
                "delta_blocks_pct": None,
            }

        # 1-hour-ago snapshot for deltas
        one_hour_ago = latest.captured_at - timedelta(hours=1)
        old_stmt = (
            select(MempoolSnapshot)
            .where(MempoolSnapshot.captured_at <= one_hour_ago)
            .order_by(desc(MempoolSnapshot.captured_at))
            .limit(1)
        )
        old = (await session.execute(old_stmt)).scalar_one_or_none()

        delta_size_pct = None
        delta_fee_pct = None
        delta_total_fee_pct = None
        delta_blocks_pct = None

        if old:
            if old.tx_count > 0:
                delta_size_pct = round(((latest.tx_count - old.tx_count) / old.tx_count) * 100, 1)
            if old.total_fee_sats > 0:
                delta_total_fee_pct = round(((latest.total_fee_sats - old.total_fee_sats) / old.total_fee_sats) * 100, 1)
            if old.median_fee > 0:
                delta_fee_pct = round(((latest.median_fee - old.median_fee) / old.median_fee) * 100, 1)
            if old.total_bytes > 0:
                delta_blocks_pct = round(((latest.total_bytes - old.total_bytes) / old.total_bytes) * 100, 1)

        return {
            "mempool_size": latest.tx_count,
            "mempool_bytes": latest.total_bytes,
            "total_fee_sats": latest.total_fee_sats,
            "median_fee": latest.median_fee,
            "blocks_to_clear": 0,  # Requires mempool-blocks processing (deferred)
            "delta_size_pct": delta_size_pct,
            "delta_fee_pct": delta_fee_pct,
            "delta_total_fee_pct": delta_total_fee_pct,
            "delta_blocks_pct": delta_blocks_pct,
        }


# =============================================================================
# RECENT BLOCKS
# =============================================================================

async def query_recent_blocks(limit: int = 10) -> dict:
    """Query confirmed blocks ordered by height descending.

    Returns:
        Dict matching RecentBlocksResponse fields.
    """
    async with async_session() as session:
        stmt = (
            select(BlockRecord)
            .order_by(desc(BlockRecord.height))
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        if not rows:
            return {"blocks": [], "latest_height": None}

        blocks = []
        for row in rows:
            # Convert unix timestamp to ISO 8601
            ts = datetime.fromtimestamp(row.timestamp, tz=timezone.utc).isoformat()
            blocks.append({
                "height": row.height,
                "timestamp": ts,
                "tx_count": row.tx_count,
                "size_bytes": row.size,
                "median_fee": row.median_fee,
                "total_fees_sats": row.total_fees,
                "fee_range": [],  # Not stored in current BlockRecord schema
                "pool_name": None,  # Not stored in current BlockRecord schema
            })

        return {
            "blocks": blocks,
            "latest_height": blocks[0]["height"] if blocks else None,
        }


# =============================================================================
# ORCHESTRATOR STATUS (Market Metrics)
# =============================================================================

async def query_orchestrator_status() -> dict:
    """Build market status from PostgreSQL data.

    Calculates EMA, trend, traffic level from stored blocks and snapshots.
    Strategy evaluation (PATIENT/RELIABLE) deferred to future phase.

    Returns:
        Dict matching OrchestratorStatusResponse fields.
    """
    async with async_session() as session:
        # Current median fee from latest snapshot
        latest_snap = (await session.execute(
            select(MempoolSnapshot)
            .order_by(desc(MempoolSnapshot.captured_at))
            .limit(1)
        )).scalar_one_or_none()

        current_median_fee = latest_snap.median_fee if latest_snap else 0.0
        mempool_size = latest_snap.tx_count if latest_snap else 0

        # Historical median from last 100 blocks
        block_fees_result = await session.execute(
            select(BlockRecord.median_fee)
            .order_by(desc(BlockRecord.height))
            .limit(100)
        )
        block_fees = [row[0] for row in block_fees_result.all()]

        historical_median_fee = max(1.0, sorted(block_fees)[len(block_fees) // 2]) if block_fees else 1.0

        # EMA from all blocks (ascending order)
        all_fees_result = await session.execute(
            select(BlockRecord.median_fee)
            .order_by(BlockRecord.height)
        )
        all_fees = [row[0] for row in all_fees_result.all()]

        ema_fee = _compute_ema_local(all_fees) if all_fees else 0.0
        ema_trend = _classify_ema_trend_local(all_fees)

        # Latest block height
        max_height_result = await session.execute(
            select(func.max(BlockRecord.height))
        )
        latest_height = max_height_result.scalar()

    # Fee premium
    fee_premium_pct = (
        ((current_median_fee - historical_median_fee) / historical_median_fee) * 100
        if historical_median_fee > 0
        else 0.0
    )

    # Traffic level
    if mempool_size < 10_000:
        traffic_level = "LOW"
    elif mempool_size > 50_000:
        traffic_level = "HIGH"
    else:
        traffic_level = "NORMAL"

    return {
        "current_median_fee": current_median_fee,
        "historical_median_fee": historical_median_fee,
        "ema_fee": ema_fee,
        "ema_trend": ema_trend,
        "fee_premium_pct": round(fee_premium_pct, 1),
        "traffic_level": traffic_level,
        "latest_block_height": latest_height,
        "patient": {
            "action": "WAIT",
            "recommended_fee": max(1, int(ema_fee * 0.8)),
            "confidence": 0.5,
        },
        "reliable": {
            "action": "BROADCAST",
            "recommended_fee": max(1, int(current_median_fee)),
            "confidence": 0.8,
        },
    }


# =============================================================================
# WATCHLIST (Stub — deferred to advisory phase)
# =============================================================================

async def query_watchlist_advisories() -> dict:
    """Query watchlist advisories from PostgreSQL.

    Returns:
        Dict matching WatchlistResponse fields.
    """
    # Stub — advisory pipeline not yet wired
    return {"advisories": [], "stuck_count": 0, "total_count": 0}


# =============================================================================
# EMA helpers (pure math — no DB dependency)
# =============================================================================

def _compute_ema_local(fees: list[float], window: int = 20) -> float:
    """Compute EMA-20 over fee values."""
    if not fees:
        return 0.0
    alpha = 2.0 / (window + 1)
    ema = fees[0]
    for fee in fees[1:]:
        ema = alpha * fee + (1 - alpha) * ema
    return max(1.0, ema)


def _classify_ema_trend_local(
    fees: list[float],
    window: int = 20,
    lookback: int = 5,
    threshold: float = 5.0,
) -> str:
    """Classify EMA trend as RISING, FALLING, or STABLE."""
    if len(fees) < lookback + 1:
        return "STABLE"
    ema_now = _compute_ema_local(fees, window)
    ema_prev = _compute_ema_local(fees[:-lookback], window)
    if ema_prev == 0:
        return "STABLE"
    change_pct = ((ema_now - ema_prev) / ema_prev) * 100
    if change_pct > threshold:
        return "RISING"
    elif change_pct < -threshold:
        return "FALLING"
    return "STABLE"
