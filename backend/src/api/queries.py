"""Pure SQL query functions for the FastAPI data layer.

All functions receive a DuckDB connection and return typed data.
No FastAPI imports — fully testable in isolation.
All connections must be opened with read_only=True.
"""

import json
from datetime import datetime, timezone

import duckdb


# =============================================================================
# MEMPOOL STATS (KPI Cards)
# =============================================================================

def query_mempool_stats(conn: duckdb.DuckDBPyConnection) -> dict:
    """Query latest mempool stats + next-block fee + blocks to clear.

    Returns:
        Dict matching MempoolStatsResponse fields.
    """
    # Latest mempool stats
    stats = conn.execute("""
        SELECT size, bytes, total_fee
        FROM mempool_stats
        ORDER BY ingestion_time DESC
        LIMIT 1
    """).fetchone()

    if not stats:
        return {
            "mempool_size": 0,
            "mempool_bytes": 0,
            "total_fee_sats": 0,
            "median_fee": 0.0,
            "blocks_to_clear": 0,
            "delta_size_pct": None,
            "delta_fee_pct": None,
        }

    mempool_size, mempool_bytes, total_fee_sats = stats

    # Next-block median fee from mempool_stream
    fee_row = conn.execute("""
        SELECT median_fee
        FROM mempool_stream
        WHERE block_index = 0
        ORDER BY ingestion_time DESC
        LIMIT 1
    """).fetchone()
    median_fee = fee_row[0] if fee_row else 0.0

    # Blocks to clear: count of projected blocks in latest snapshot
    blocks_row = conn.execute("""
        SELECT COUNT(*)
        FROM mempool_stream
        WHERE ingestion_time = (SELECT MAX(ingestion_time) FROM mempool_stream)
    """).fetchone()
    blocks_to_clear = blocks_row[0] if blocks_row else 0

    # 1-hour delta for mempool size
    delta_size_pct = None
    delta_fee_pct = None

    stats_1h = conn.execute("""
        SELECT size, total_fee
        FROM mempool_stats
        WHERE ingestion_time <= (
            SELECT MAX(ingestion_time) - INTERVAL 1 HOUR FROM mempool_stats
        )
        ORDER BY ingestion_time DESC
        LIMIT 1
    """).fetchone()

    if stats_1h and stats_1h[0] > 0:
        delta_size_pct = round(((mempool_size - stats_1h[0]) / stats_1h[0]) * 100, 1)

    # 1-hour delta for median fee
    fee_1h = conn.execute("""
        SELECT median_fee
        FROM mempool_stream
        WHERE block_index = 0
          AND ingestion_time <= (
              SELECT MAX(ingestion_time) - INTERVAL 1 HOUR FROM mempool_stream
          )
        ORDER BY ingestion_time DESC
        LIMIT 1
    """).fetchone()

    if fee_1h and fee_1h[0] > 0:
        delta_fee_pct = round(((median_fee - fee_1h[0]) / fee_1h[0]) * 100, 1)

    return {
        "mempool_size": mempool_size,
        "mempool_bytes": mempool_bytes,
        "total_fee_sats": total_fee_sats,
        "median_fee": median_fee,
        "blocks_to_clear": blocks_to_clear,
        "delta_size_pct": delta_size_pct,
        "delta_fee_pct": delta_fee_pct,
    }


# =============================================================================
# FEE DISTRIBUTION (Histogram)
# =============================================================================

# Fee band boundaries in sat/vB
_FEE_BANDS = [
    (0, 5, "1-5"),
    (5, 10, "5-10"),
    (10, 15, "10-15"),
    (15, 20, "15-20"),
    (20, 30, "20-30"),
    (30, 50, "30-50"),
    (50, float("inf"), "50+"),
]


def query_fee_distribution(conn: duckdb.DuckDBPyConnection) -> dict:
    """Build fee histogram from the latest mempool_stream snapshot.

    Uses fee_range (p0, p10, p25, p50, p75, p90, p100) and n_tx from each
    projected block to estimate transaction distribution across fee bands.

    Returns:
        Dict matching FeeDistributionResponse fields.
    """
    rows = conn.execute("""
        SELECT fee_range, n_tx
        FROM mempool_stream
        WHERE ingestion_time = (SELECT MAX(ingestion_time) FROM mempool_stream)
        ORDER BY block_index
    """).fetchall()

    if not rows:
        return {"bands": [], "total_txs": 0, "peak_band": "N/A"}

    # Aggregate fee_range data across all projected blocks
    # fee_range = [min, p10, p25, p50, p75, p90, max]
    # Percentile weights: approximate tx distribution based on percentile ranges
    percentile_weights = [0.10, 0.15, 0.25, 0.25, 0.15, 0.10]

    band_counts: dict[str, int] = {label: 0 for _, _, label in _FEE_BANDS}
    total_txs = 0

    for fee_range_json, n_tx in rows:
        if isinstance(fee_range_json, str):
            fee_range = json.loads(fee_range_json)
        else:
            fee_range = fee_range_json

        if not fee_range or len(fee_range) < 7:
            continue

        total_txs += n_tx

        # Map percentile midpoints to fee bands
        percentile_midpoints = [
            fee_range[0],                              # p0-p10 midpoint
            (fee_range[1] + fee_range[2]) / 2,         # p10-p25
            (fee_range[2] + fee_range[3]) / 2,         # p25-p50
            (fee_range[3] + fee_range[4]) / 2,         # p50-p75
            (fee_range[4] + fee_range[5]) / 2,         # p75-p90
            fee_range[6],                              # p90-p100
        ]

        for midpoint, weight in zip(percentile_midpoints, percentile_weights):
            count = int(n_tx * weight)
            for low, high, label in _FEE_BANDS:
                if low <= midpoint < high:
                    band_counts[label] += count
                    break

    # Convert to response format
    bands = []
    for _, _, label in _FEE_BANDS:
        count = band_counts[label]
        pct = round((count / total_txs * 100), 1) if total_txs > 0 else 0.0
        bands.append({"range": label, "count": count, "pct": pct})

    peak_band = max(bands, key=lambda b: b["pct"])["range"] if bands else "N/A"

    return {"bands": bands, "total_txs": total_txs, "peak_band": peak_band}


# =============================================================================
# RECENT BLOCKS
# =============================================================================

def query_recent_blocks(conn: duckdb.DuckDBPyConnection, limit: int = 10) -> dict:
    """Query confirmed blocks from block_history.

    Returns:
        Dict matching RecentBlocksResponse fields.
    """
    rows = conn.execute("""
        SELECT height, ingestion_time, n_tx, block_size,
               median_fee, total_fees, fee_range, pool_name
        FROM block_history
        ORDER BY height DESC
        LIMIT ?
    """, [limit]).fetchall()

    if not rows:
        return {"blocks": [], "latest_height": None}

    blocks = []
    for row in rows:
        height, ingestion_time, n_tx, block_size, median_fee, total_fees, fee_range_json, pool_name = row

        # Parse fee_range
        if isinstance(fee_range_json, str):
            fee_range = json.loads(fee_range_json)
        elif fee_range_json is not None:
            fee_range = fee_range_json
        else:
            fee_range = []

        # Format timestamp
        if isinstance(ingestion_time, datetime):
            timestamp_str = ingestion_time.isoformat()
        else:
            timestamp_str = str(ingestion_time)

        blocks.append({
            "height": height,
            "timestamp": timestamp_str,
            "tx_count": n_tx,
            "size_bytes": block_size,
            "median_fee": median_fee,
            "total_fees_sats": total_fees,
            "fee_range": fee_range,
            "pool_name": pool_name,
        })

    return {
        "blocks": blocks,
        "latest_height": blocks[0]["height"] if blocks else None,
    }


# =============================================================================
# ORCHESTRATOR STATUS
# =============================================================================

def query_orchestrator_status(
    market_conn: duckdb.DuckDBPyConnection,
) -> dict:
    """Build orchestrator status from DuckDB market data.

    Replicates the logic from tools.get_market_context() but returns
    a flat dict for API serialization. Avoids importing the orchestrator
    module to keep the API layer decoupled.

    Returns:
        Dict matching OrchestratorStatusResponse fields.
    """
    from src.config import settings

    # Current median fee from mempool_stream (next block)
    fee_row = market_conn.execute("""
        SELECT median_fee
        FROM mempool_stream
        WHERE block_index = 0
        ORDER BY ingestion_time DESC
        LIMIT 1
    """).fetchone()
    current_median_fee = fee_row[0] if fee_row else 0.0

    # Historical median from block_history
    hist_row = market_conn.execute("""
        SELECT MEDIAN(median_fee) FROM (
            SELECT median_fee FROM block_history
            ORDER BY height DESC LIMIT 100
        )
    """).fetchone()
    historical_median_fee = max(1.0, hist_row[0]) if hist_row and hist_row[0] else 1.0

    # EMA-20 from block_history
    ema_rows = market_conn.execute("""
        SELECT median_fee FROM block_history ORDER BY height ASC
    """).fetchall()
    ema_fees = [r[0] for r in ema_rows] if ema_rows else []

    ema_fee = _compute_ema_local(ema_fees) if ema_fees else 0.0
    ema_trend = _classify_ema_trend_local(ema_fees)

    # Fee premium
    fee_premium_pct = (
        ((current_median_fee - historical_median_fee) / historical_median_fee) * 100
        if historical_median_fee > 0
        else 0.0
    )

    # Mempool stats for traffic level
    stats_row = market_conn.execute("""
        SELECT size FROM mempool_stats ORDER BY ingestion_time DESC LIMIT 1
    """).fetchone()
    mempool_size = stats_row[0] if stats_row else 0

    if mempool_size < 10_000:
        traffic_level = "LOW"
    elif mempool_size > 50_000:
        traffic_level = "HIGH"
    else:
        traffic_level = "NORMAL"

    # Latest block height
    height_row = market_conn.execute("""
        SELECT MAX(height) FROM block_history
    """).fetchone()
    latest_height = height_row[0] if height_row and height_row[0] else None

    return {
        "strategy_mode": settings.strategy_mode,
        "current_median_fee": current_median_fee,
        "historical_median_fee": historical_median_fee,
        "ema_fee": ema_fee,
        "ema_trend": ema_trend,
        "fee_premium_pct": round(fee_premium_pct, 1),
        "traffic_level": traffic_level,
        "latest_block_height": latest_height,
    }


# =============================================================================
# WATCHLIST (Advisors)
# =============================================================================

def query_watchlist_advisories(
    history_conn: duckdb.DuckDBPyConnection,
    target_fee_rate: float,
) -> dict:
    """Query watchlist entries and compute advisory actions.

    Args:
        history_conn: Connection to agent_history.duckdb.
        target_fee_rate: Recommended fee rate from strategy engine.

    Returns:
        Dict matching WatchlistResponse fields.
    """
    from src.strategies.advisors import evaluate_rbf, evaluate_cpfp

    # Check if watchlist table exists
    tables = history_conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name = 'watchlist'"
    ).fetchall()

    if not tables:
        return {"advisories": [], "stuck_count": 0, "total_count": 0}

    rows = history_conn.execute("""
        SELECT txid, role, status, fee, fee_rate
        FROM watchlist
        ORDER BY added_at DESC
    """).fetchall()

    advisories = []
    stuck_count = 0

    for txid, role, status, fee_sats, fee_rate in rows:
        if status == "CONFIRMED":
            advisories.append({
                "txid": txid,
                "role": role,
                "status": status,
                "current_fee_rate": fee_rate,
                "action": "No action needed",
                "action_type": "None",
                "cost_sats": None,
            })
            continue

        # PENDING transaction — run advisor
        if fee_rate is None or fee_sats is None:
            advisories.append({
                "txid": txid,
                "role": role,
                "status": "Pending",
                "current_fee_rate": fee_rate,
                "action": "Monitor only",
                "action_type": "None",
                "cost_sats": None,
            })
            continue

        if role == "SENDER":
            vsize = fee_sats / fee_rate if fee_rate > 0 else 225.0
            advice = evaluate_rbf(
                original_fee_sats=fee_sats,
                original_fee_rate=fee_rate,
                original_vsize=vsize,
                target_fee_rate=target_fee_rate,
            )
            if advice.is_stuck:
                stuck_count += 1
                advisories.append({
                    "txid": txid,
                    "role": role,
                    "status": "Stuck",
                    "current_fee_rate": fee_rate,
                    "action": f"RBF to {advice.target_fee_rate:.1f} sat/vB",
                    "action_type": "RBF",
                    "cost_sats": advice.target_fee_sats,
                })
            else:
                advisories.append({
                    "txid": txid,
                    "role": role,
                    "status": "Pending",
                    "current_fee_rate": fee_rate,
                    "action": "Monitor only",
                    "action_type": "None",
                    "cost_sats": None,
                })

        elif role == "RECEIVER":
            vsize = fee_sats / fee_rate if fee_rate > 0 else 225.0
            advice = evaluate_cpfp(
                parent_fee_sats=fee_sats,
                parent_vsize=vsize,
                target_fee_rate=target_fee_rate,
            )
            if advice.is_stuck:
                stuck_count += 1
                advisories.append({
                    "txid": txid,
                    "role": role,
                    "status": "Stuck",
                    "current_fee_rate": fee_rate,
                    "action": f"CPFP Child: {target_fee_rate:.1f} sat/vB",
                    "action_type": "CPFP",
                    "cost_sats": advice.child_fee_sats,
                })
            else:
                advisories.append({
                    "txid": txid,
                    "role": role,
                    "status": "Pending",
                    "current_fee_rate": fee_rate,
                    "action": "Monitor only",
                    "action_type": "None",
                    "cost_sats": None,
                })

    return {
        "advisories": advisories,
        "stuck_count": stuck_count,
        "total_count": len(rows),
    }


# =============================================================================
# EMA helpers (local copies to avoid importing orchestrator.tools)
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
