"""Database query tools for the AI Orchestrator Agent.

Provides read-only access to DuckDB for mempool market analysis.
"""

import os
from typing import Literal

import duckdb
from loguru import logger

from src.orchestrator.schemas import MempoolContext


# Configuration from environment
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "mempool_data.duckdb")
HISTORICAL_WINDOW_ROWS = 100  # Number of rows for historical median calculation


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
    
    Returns:
        MempoolContext with current and historical fee data.
        
    Raises:
        RuntimeError: If database queries fail or return no data.
    """
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    
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
        
        # Get current median fee (next block, block_index=0)
        current_fee_query = """
            SELECT median_fee
            FROM projected_blocks
            WHERE block_index = 0
            ORDER BY ingestion_time DESC
            LIMIT 1
        """
        current_fee_result = conn.execute(current_fee_query).fetchone()
        
        if not current_fee_result:
            raise RuntimeError("No projected_blocks data available")
        
        current_median_fee = current_fee_result[0]
        
        # Compute historical median over recent window
        historical_query = f"""
            SELECT MEDIAN(median_fee) as historical_median
            FROM (
                SELECT median_fee
                FROM projected_blocks
                WHERE block_index = 0
                ORDER BY ingestion_time DESC
                LIMIT {HISTORICAL_WINDOW_ROWS}
            )
        """
        historical_result = conn.execute(historical_query).fetchone()
        
        if not historical_result or historical_result[0] is None:
            # Fallback to current if no historical data
            historical_median_fee = current_median_fee
            logger.warning("Insufficient historical data, using current fee as baseline")
        else:
            historical_median_fee = historical_result[0]
        
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
