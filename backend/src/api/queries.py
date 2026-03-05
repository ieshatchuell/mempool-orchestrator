"""Async query functions for the FastAPI data layer.

All functions use SQLAlchemy async sessions to read from PostgreSQL.
No framework imports — fully testable in isolation.
Read-only: no INSERT/UPDATE/DELETE operations.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc

from src.infrastructure.database.session import async_session
from src.infrastructure.database.models import BlockRecord, MempoolSnapshot, MempoolBlockProjection, AdvisoryRecord


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

        # Blocks to clear: count of projected mempool blocks
        blocks_to_clear_result = await session.execute(
            select(func.count()).select_from(MempoolBlockProjection)
        )
        blocks_to_clear = blocks_to_clear_result.scalar() or 0

        return {
            "mempool_size": latest.tx_count,
            "mempool_bytes": latest.total_bytes,
            "total_fee_sats": latest.total_fee_sats,
            "median_fee": latest.median_fee,
            "blocks_to_clear": blocks_to_clear,
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
                "fee_range": row.fee_range if row.fee_range else [],
                "pool_name": row.pool_name,
            })

        return {
            "blocks": blocks,
            "latest_height": blocks[0]["height"] if blocks else None,
        }


# =============================================================================
# WATCHLIST (Stub — deferred to advisory phase)
# =============================================================================

async def query_watchlist_advisories() -> dict:
    """Query watchlist advisories from PostgreSQL.

    Returns:
        Dict matching WatchlistResponse fields.
    """
    async with async_session() as session:
        stmt = (
            select(AdvisoryRecord)
            .order_by(desc(AdvisoryRecord.created_at))
            .limit(20)
        )
        rows = (await session.execute(stmt)).scalars().all()

        if not rows:
            return {"advisories": [], "stuck_count": 0, "total_count": 0}

        advisories = []
        for r in rows:
            advisories.append({
                "txid": r.txid,
                "status": "Stuck" if r.action == "BUMP" else "Pending",
                "current_fee_rate": r.current_fee_rate,
                "rbf": {
                    "action": f"Replace with {r.target_fee_rate:.1f} sat/vB",
                    "cost_sats": r.rbf_fee_sats,
                } if r.rbf_fee_sats else None,
                "cpfp": {
                    "action": f"Child pays to reach {r.target_fee_rate:.1f} sat/vB",
                    "cost_sats": r.cpfp_fee_sats,
                } if r.cpfp_fee_sats else None,
            })

        stuck_count = sum(1 for r in rows if r.action == "BUMP")
        return {
            "advisories": advisories,
            "stuck_count": stuck_count,
            "total_count": len(rows),
        }


# =============================================================================
# ORCHESTRATOR STATUS (Market Metrics — pure SQL/Python, no external service)
# =============================================================================

async def query_orchestrator_status() -> dict:
    """Build market status from PostgreSQL data.

    Calculates EMA, trend, traffic level from stored blocks and snapshots.
    Serves the Dashboard's Strategy & Trend card.

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

    # Fee premium — guard against zero values (Premium -100% fix)
    if current_median_fee <= 0 or historical_median_fee <= 0:
        fee_premium_pct = 0.0
    else:
        fee_premium_pct = (
            ((current_median_fee - historical_median_fee) / historical_median_fee) * 100
        )

    # Traffic level
    if mempool_size < 10_000:
        traffic_level = "LOW"
    elif mempool_size > 50_000:
        traffic_level = "HIGH"
    else:
        traffic_level = "NORMAL"

    # Real confidence calculation
    patient_conf, reliable_conf = _compute_confidence(
        current_fee=current_median_fee,
        ema_fee=ema_fee,
        trend=ema_trend,
        fee_premium_pct=fee_premium_pct,
    )

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
            "confidence": patient_conf,
        },
        "reliable": {
            "action": "BROADCAST",
            "recommended_fee": max(1, int(current_median_fee)),
            "confidence": reliable_conf,
        },
    }


# =============================================================================
# Confidence calculation (pure math — no DB dependency)
# =============================================================================


def _compute_confidence(
    current_fee: float,
    ema_fee: float,
    trend: str,
    fee_premium_pct: float,
) -> tuple[float, float]:
    """Compute confidence for PATIENT and RELIABLE strategies.

    Logic:
    - Base confidence starts at 0.5
    - PATIENT gains confidence when:
      - EMA trend is FALLING (market cooling → waiting pays off)
      - fee_premium is HIGH (current >> historical → likely to drop)
      - EMA and current are diverging (volatility = opportunity to wait)
    - RELIABLE gains confidence when:
      - EMA trend is STABLE or RISING (market predictable/heating)
      - fee_premium is LOW (current ≈ historical → fair price)
      - EMA and current are converging (low volatility = safe to broadcast)

    Returns:
        (patient_confidence, reliable_confidence) — both clamped [0.1, 0.95]
    """
    # Divergence ratio: |current - ema| / ema
    divergence = abs(current_fee - ema_fee) / max(ema_fee, 1.0)

    # Patient confidence
    patient = 0.5
    if trend == "FALLING":
        patient += 0.15
    elif trend == "RISING":
        patient -= 0.15
    if fee_premium_pct > 20:
        patient += 0.15
    elif fee_premium_pct < -10:
        patient -= 0.1
    patient += min(divergence * 0.3, 0.15)  # High divergence = wait opportunity

    # Reliable confidence
    reliable = 0.5
    if trend == "STABLE":
        reliable += 0.15
    elif trend == "RISING":
        reliable += 0.1
    elif trend == "FALLING":
        reliable -= 0.1
    if abs(fee_premium_pct) < 10:
        reliable += 0.15
    reliable += max(0.15 - divergence * 0.3, 0)  # Low divergence = safe to act

    return (
        round(max(0.1, min(0.95, patient)), 2),
        round(max(0.1, min(0.95, reliable)), 2),
    )


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

