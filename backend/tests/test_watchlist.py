"""Unit tests for the Watchlist persistence layer.

Tests CRUD operations, dedup protection, status transitions,
and Pydantic validation for WatchlistEntry/WatchlistRecord.
"""

from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest
from pydantic import ValidationError

from src.storage.watchlist import Watchlist, WatchlistEntry, WatchlistRecord


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def watchlist(tmp_path: Path) -> Watchlist:
    """Create a fresh Watchlist with a temporary DuckDB database."""
    db_path = str(tmp_path / "test_watchlist.duckdb")
    wl = Watchlist(db_path=db_path)
    yield wl
    wl.close()


SAMPLE_TXID = "a" * 64  # Valid 64-char hex string
SAMPLE_TXID_2 = "b" * 64


# =============================================================================
# Table Schema
# =============================================================================

class TestWatchlistSchema:
    """Tests for DuckDB table creation and schema."""

    def test_creates_table(self, tmp_path: Path) -> None:
        """Verify that initializing Watchlist creates the table."""
        db_path = str(tmp_path / "test_schema.duckdb")
        wl = Watchlist(db_path=db_path)
        wl.close()

        conn = duckdb.connect(db_path, read_only=True)
        try:
            result = conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'watchlist'
            """).fetchone()
            assert result is not None
            assert result[0] == "watchlist"
        finally:
            conn.close()

    def test_correct_columns(self, tmp_path: Path) -> None:
        """Verify all expected columns exist."""
        db_path = str(tmp_path / "test_cols.duckdb")
        wl = Watchlist(db_path=db_path)
        wl.close()

        conn = duckdb.connect(db_path, read_only=True)
        try:
            columns = conn.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'watchlist'
                ORDER BY ordinal_position
            """).fetchall()
            col_names = [c[0] for c in columns]
            assert col_names == [
                "txid", "role", "added_at", "status",
                "fee", "fee_rate", "confirmed_at", "block_height",
            ]
        finally:
            conn.close()


# =============================================================================
# CRUD Operations
# =============================================================================

class TestWatchlistCRUD:
    """Tests for add_tx, remove_tx, get_active, get_all, mark_confirmed."""

    def test_add_tx(self, watchlist: Watchlist) -> None:
        """Adding a valid tx returns True."""
        entry = WatchlistEntry(txid=SAMPLE_TXID, role="SENDER")
        assert watchlist.add_tx(entry) is True

    def test_add_tx_with_fee(self, watchlist: Watchlist) -> None:
        """Adding a tx with fee data stores it correctly."""
        entry = WatchlistEntry(txid=SAMPLE_TXID, role="RECEIVER")
        watchlist.add_tx(entry, fee=1500, fee_rate=8.5)

        records = watchlist.get_all()
        assert len(records) == 1
        assert records[0].fee == 1500
        assert records[0].fee_rate == 8.5

    def test_add_tx_dedup(self, watchlist: Watchlist) -> None:
        """Adding the same txid twice returns False (no duplicate)."""
        entry = WatchlistEntry(txid=SAMPLE_TXID, role="SENDER")
        assert watchlist.add_tx(entry) is True
        assert watchlist.add_tx(entry) is False

        # Only one record should exist
        assert len(watchlist.get_all()) == 1

    def test_remove_tx(self, watchlist: Watchlist) -> None:
        """Removing an existing tx returns True."""
        entry = WatchlistEntry(txid=SAMPLE_TXID, role="SENDER")
        watchlist.add_tx(entry)
        assert watchlist.remove_tx(SAMPLE_TXID) is True
        assert len(watchlist.get_all()) == 0

    def test_remove_tx_not_found(self, watchlist: Watchlist) -> None:
        """Removing a non-existent txid returns False."""
        assert watchlist.remove_tx(SAMPLE_TXID) is False

    def test_get_active_only_pending(self, watchlist: Watchlist) -> None:
        """get_active() returns only PENDING transactions."""
        entry1 = WatchlistEntry(txid=SAMPLE_TXID, role="SENDER")
        entry2 = WatchlistEntry(txid=SAMPLE_TXID_2, role="RECEIVER")
        watchlist.add_tx(entry1)
        watchlist.add_tx(entry2)

        # Confirm one
        watchlist.mark_confirmed(SAMPLE_TXID, block_height=900000)

        active = watchlist.get_active()
        assert len(active) == 1
        assert active[0].txid == SAMPLE_TXID_2
        assert active[0].status == "PENDING"

    def test_get_all_includes_confirmed(self, watchlist: Watchlist) -> None:
        """get_all() returns both PENDING and CONFIRMED entries."""
        entry1 = WatchlistEntry(txid=SAMPLE_TXID, role="SENDER")
        entry2 = WatchlistEntry(txid=SAMPLE_TXID_2, role="RECEIVER")
        watchlist.add_tx(entry1)
        watchlist.add_tx(entry2)
        watchlist.mark_confirmed(SAMPLE_TXID, block_height=900000)

        all_records = watchlist.get_all()
        assert len(all_records) == 2
        statuses = {r.txid: r.status for r in all_records}
        assert statuses[SAMPLE_TXID] == "CONFIRMED"
        assert statuses[SAMPLE_TXID_2] == "PENDING"

    def test_count_active(self, watchlist: Watchlist) -> None:
        """count_active() returns count of PENDING entries only."""
        assert watchlist.count_active() == 0

        entry = WatchlistEntry(txid=SAMPLE_TXID, role="SENDER")
        watchlist.add_tx(entry)
        assert watchlist.count_active() == 1

        watchlist.mark_confirmed(SAMPLE_TXID, block_height=900000)
        assert watchlist.count_active() == 0


# =============================================================================
# Status Transitions
# =============================================================================

class TestStatusTransitions:
    """Tests for PENDING → CONFIRMED state machine."""

    def test_mark_confirmed(self, watchlist: Watchlist) -> None:
        """Marking a PENDING tx as confirmed updates all fields."""
        entry = WatchlistEntry(txid=SAMPLE_TXID, role="SENDER")
        watchlist.add_tx(entry)

        result = watchlist.mark_confirmed(SAMPLE_TXID, block_height=900000)
        assert result is True

        records = watchlist.get_all()
        confirmed = records[0]
        assert confirmed.status == "CONFIRMED"
        assert confirmed.block_height == 900000
        assert confirmed.confirmed_at is not None

    def test_mark_confirmed_not_found(self, watchlist: Watchlist) -> None:
        """Marking a non-existent txid returns False."""
        assert watchlist.mark_confirmed("f" * 64, block_height=900000) is False

    def test_mark_confirmed_idempotent(self, watchlist: Watchlist) -> None:
        """Marking an already-confirmed tx returns False (no double-update)."""
        entry = WatchlistEntry(txid=SAMPLE_TXID, role="SENDER")
        watchlist.add_tx(entry)

        assert watchlist.mark_confirmed(SAMPLE_TXID, block_height=900000) is True
        assert watchlist.mark_confirmed(SAMPLE_TXID, block_height=900001) is False


# =============================================================================
# Pydantic Validation
# =============================================================================

class TestWatchlistValidation:
    """Tests for WatchlistEntry and WatchlistRecord validation."""

    def test_valid_entry(self) -> None:
        """Valid 64-char hex txid and valid role."""
        entry = WatchlistEntry(txid=SAMPLE_TXID, role="SENDER")
        assert entry.txid == SAMPLE_TXID.lower()
        assert entry.role == "SENDER"

    def test_invalid_txid_length(self) -> None:
        """txid must be exactly 64 characters."""
        with pytest.raises(ValidationError):
            WatchlistEntry(txid="abcd", role="SENDER")

    def test_invalid_txid_chars(self) -> None:
        """txid must be hex characters only."""
        with pytest.raises(ValidationError):
            WatchlistEntry(txid="g" * 64, role="SENDER")

    def test_invalid_role(self) -> None:
        """role must be SENDER or RECEIVER."""
        with pytest.raises(ValidationError):
            WatchlistEntry(txid=SAMPLE_TXID, role="OBSERVER")

    def test_txid_normalized_to_lowercase(self) -> None:
        """Mixed-case txid gets normalized to lowercase."""
        entry = WatchlistEntry(txid="A" * 64, role="SENDER")
        assert entry.txid == "a" * 64

    def test_record_defaults(self) -> None:
        """WatchlistRecord has sensible defaults."""
        record = WatchlistRecord(
            txid=SAMPLE_TXID,
            role="SENDER",
            added_at=datetime.now(timezone.utc),
        )
        assert record.status == "PENDING"
        assert record.fee is None
        assert record.confirmed_at is None
        assert record.block_height is None
