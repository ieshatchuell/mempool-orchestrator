"""Watchlist persistence layer for tracking Bitcoin transactions.

Stores tracked TXIDs in a DuckDB table with their role (SENDER/RECEIVER)
and confirmation status. Uses the same isolated DB as agent_history to
avoid file lock conflicts with the market data DB.

Table: watchlist
- txid: Primary key (64-char hex string)
- role: SENDER or RECEIVER (determines RBF vs CPFP in Session 8)
- added_at: When the tx was added to the watchlist
- status: PENDING (in mempool) or CONFIRMED (mined)
- fee: Transaction fee in satoshis (from API lookup)
- fee_rate: Fee rate in sat/vB (fee / vsize)
- confirmed_at: Timestamp when confirmation was detected
- block_height: Block height where tx was mined
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import duckdb
from loguru import logger
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Models
# =============================================================================

class WatchlistEntry(BaseModel):
    """Input model for adding a transaction to the watchlist."""

    txid: str = Field(..., description="Transaction ID (64-char hex string)", min_length=64, max_length=64)
    role: Literal["SENDER", "RECEIVER"] = Field(
        ...,
        description="User's role: SENDER (can RBF) or RECEIVER (can CPFP)",
    )

    @field_validator("txid")
    @classmethod
    def validate_txid_hex(cls, v: str) -> str:
        """Ensure txid is a valid 64-char hex string."""
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError(f"txid must be a hex string, got: {v}")
        return v.lower()


class WatchlistRecord(BaseModel):
    """Full record from the watchlist table."""

    txid: str
    role: Literal["SENDER", "RECEIVER"]
    added_at: datetime
    status: Literal["PENDING", "CONFIRMED"] = "PENDING"
    fee: int | None = None
    fee_rate: float | None = None
    confirmed_at: datetime | None = None
    block_height: int | None = None


# =============================================================================
# Persistence
# =============================================================================

class Watchlist:
    """DuckDB-backed watchlist for tracking Bitcoin transactions.
    
    Uses a persistent connection with WAL mode for safe concurrent reads.
    Stores in the same directory as agent_history (data/history/).
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from src.config import settings
            db_path = str(Path(settings.agent_history_path).resolve())
        
        self._db_path = db_path
        self._conn = duckdb.connect(db_path)
        self._create_table()
        logger.debug(f"Watchlist initialized: {db_path}")

    def _create_table(self) -> None:
        """Create watchlist table if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                txid VARCHAR PRIMARY KEY,
                role VARCHAR NOT NULL,
                added_at TIMESTAMP NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'PENDING',
                fee INTEGER,
                fee_rate DOUBLE,
                confirmed_at TIMESTAMP,
                block_height INTEGER
            )
        """)

    def add_tx(self, entry: WatchlistEntry, fee: int | None = None, fee_rate: float | None = None) -> bool:
        """Add a transaction to the watchlist.
        
        Args:
            entry: Validated WatchlistEntry with txid and role.
            fee: Optional transaction fee in satoshis.
            fee_rate: Optional fee rate in sat/vB.
            
        Returns:
            True if inserted, False if txid already exists (dedup).
        """
        # Check for existing entry (dedup)
        existing = self._conn.execute(
            "SELECT txid FROM watchlist WHERE txid = ?",
            [entry.txid],
        ).fetchone()

        if existing:
            logger.debug(f"Watchlist: txid {entry.txid[:16]}... already tracked")
            return False

        self._conn.execute(
            """
            INSERT INTO watchlist (txid, role, added_at, status, fee, fee_rate)
            VALUES (?, ?, ?, 'PENDING', ?, ?)
            """,
            [
                entry.txid,
                entry.role,
                datetime.now(timezone.utc),
                fee,
                fee_rate,
            ],
        )
        logger.info(f"👁️ Watchlist: Tracking {entry.txid[:16]}... as {entry.role}")
        return True

    def remove_tx(self, txid: str) -> bool:
        """Remove a transaction from the watchlist.
        
        Returns:
            True if removed, False if txid not found.
        """
        count_before = self._conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE txid = ?", [txid]
        ).fetchone()[0]

        if count_before == 0:
            return False

        self._conn.execute("DELETE FROM watchlist WHERE txid = ?", [txid])
        logger.info(f"🗑️ Watchlist: Removed {txid[:16]}...")
        return True

    def get_active(self) -> list[WatchlistRecord]:
        """Get all PENDING (unconfirmed) transactions.
        
        Returns:
            List of WatchlistRecord for transactions still in mempool.
        """
        rows = self._conn.execute(
            """
            SELECT txid, role, added_at, status, fee, fee_rate, confirmed_at, block_height
            FROM watchlist
            WHERE status = 'PENDING'
            ORDER BY added_at ASC
            """
        ).fetchall()

        return [
            WatchlistRecord(
                txid=r[0], role=r[1], added_at=r[2], status=r[3],
                fee=r[4], fee_rate=r[5], confirmed_at=r[6], block_height=r[7],
            )
            for r in rows
        ]

    def get_all(self) -> list[WatchlistRecord]:
        """Get all transactions (PENDING + CONFIRMED) for dashboard display.
        
        Returns:
            List of all WatchlistRecord entries.
        """
        rows = self._conn.execute(
            """
            SELECT txid, role, added_at, status, fee, fee_rate, confirmed_at, block_height
            FROM watchlist
            ORDER BY added_at DESC
            """
        ).fetchall()

        return [
            WatchlistRecord(
                txid=r[0], role=r[1], added_at=r[2], status=r[3],
                fee=r[4], fee_rate=r[5], confirmed_at=r[6], block_height=r[7],
            )
            for r in rows
        ]

    def mark_confirmed(self, txid: str, block_height: int) -> bool:
        """Mark a transaction as confirmed (mined).
        
        Args:
            txid: Transaction ID to update.
            block_height: Block height where tx was confirmed.
            
        Returns:
            True if updated, False if txid not found or already confirmed.
        """
        result = self._conn.execute(
            "SELECT status FROM watchlist WHERE txid = ?", [txid]
        ).fetchone()

        if not result or result[0] == "CONFIRMED":
            return False

        self._conn.execute(
            """
            UPDATE watchlist
            SET status = 'CONFIRMED',
                confirmed_at = ?,
                block_height = ?
            WHERE txid = ?
            """,
            [datetime.now(timezone.utc), block_height, txid],
        )
        logger.success(f"🎯 Watchlist: {txid[:16]}... confirmed in block {block_height}")
        return True

    def count_active(self) -> int:
        """Count PENDING transactions."""
        return self._conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE status = 'PENDING'"
        ).fetchone()[0]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
