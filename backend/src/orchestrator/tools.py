"""Database query tools for the AI Orchestrator Agent.

Provides read-only access to DuckDB for mempool market analysis.

Data sources:
- mempool_stats: Mempool size, bytes, fees (from WebSocket stats)
- mempool_stream: Speculative projected blocks (from WebSocket mempool-blocks)
- block_history: Confirmed mined blocks (from backfill + WebSocket block signals)
"""

import os
from pathlib import Path
from typing import Literal

import duckdb
from loguru import logger

from src.config import settings
from src.orchestrator.schemas import MempoolContext


# Historical window for baseline calculation
HISTORICAL_WINDOW_ROWS = 100  # Number of confirmed blocks for historical median


def _classify_traffic(mempool_size: int) -> Literal["LOW", "NORMAL", "HIGH"]:
    """Classify mempool traffic level based on transaction count.
    
    Thresholds based on typical Bitcoin mempool activity:
    - LOW: < 10,000 transactions (mempool clearing)
    - NORMAL: 10,000 - 50,000 transactions (typical)
    - HIGH: > 50,000 transactions (congested)
    """
    if mempool_size < 10_000:
        return "LOW"
    elif mempool_size > 50_000:
        return "HIGH"
    return "NORMAL"


def get_market_context() -> MempoolContext:
    """Query DuckDB for current mempool state and compute market context.
    
    Data flow:
    - Current fee: from mempool_stream (latest projected next block)
    - Baseline fee: from block_history (confirmed blocks, stable)
    - Mempool stats: from mempool_stats (current mempool state)
    
    Returns:
        MempoolContext with current and historical fee data.
        
    Raises:
        RuntimeError: If database queries fail or return no data.
    """
    db_path = str(Path(settings.duckdb_path).resolve())
    conn = duckdb.connect(db_path, read_only=True)
    
    try:
        # Get latest mempool stats
        stats_query = """
            SELECT size, bytes
            FROM mempool_stats
            ORDER BY ingestion_time DESC
            LIMIT 1
        """
        stats_result = conn.execute(stats_query).fetchone()
        
        if not stats_result:
            raise RuntimeError("No mempool_stats data available")
        
        mempool_size, mempool_bytes = stats_result
        
        # Get current median fee from mempool_stream (next block projection)
        current_fee_query = """
            SELECT median_fee
            FROM mempool_stream
            WHERE block_index = 0
            ORDER BY ingestion_time DESC
            LIMIT 1
        """
        current_fee_result = conn.execute(current_fee_query).fetchone()
        
        if not current_fee_result:
            raise RuntimeError("No mempool_stream data available")
        
        current_median_fee = current_fee_result[0]
        
        # Compute historical median from block_history (confirmed blocks)
        historical_query = f"""
            SELECT MEDIAN(median_fee) as historical_median
            FROM (
                SELECT median_fee
                FROM block_history
                ORDER BY height DESC
                LIMIT {HISTORICAL_WINDOW_ROWS}
            )
        """
        historical_result = conn.execute(historical_query).fetchone()
        
        if not historical_result or historical_result[0] is None:
            # Fallback to current if no historical data
            historical_median_fee = current_median_fee
            logger.warning("Insufficient historical data, using current fee as baseline")
        else:
            # Apply minrelaytxfee floor (1 sat/vB) at read time, not in the query
            historical_median_fee = max(1.0, historical_result[0])
        
        # Calculate fee premium percentage
        if historical_median_fee > 0:
            fee_premium_pct = ((current_median_fee - historical_median_fee) / historical_median_fee) * 100
        else:
            fee_premium_pct = 0.0
        
        # Classify traffic level
        traffic_level = _classify_traffic(mempool_size)
        
        logger.debug(
            f"Market context: current_fee={current_median_fee:.2f}, "
            f"historical_fee={historical_median_fee:.2f}, "
            f"premium={fee_premium_pct:.1f}%, traffic={traffic_level}"
        )
        
        return MempoolContext(
            current_median_fee=current_median_fee,
            historical_median_fee=historical_median_fee,
            mempool_size=mempool_size,
            mempool_bytes=mempool_bytes,
            fee_premium_pct=fee_premium_pct,
            traffic_level=traffic_level,
        )
        
    finally:
        conn.close()
