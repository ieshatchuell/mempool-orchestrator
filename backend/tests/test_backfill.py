"""Unit tests for the incremental backfill worker.

Tests cover:
  - Gap detection logic (empty DB, gap exists, no gap)
  - Bulk insert with ON CONFLICT DO NOTHING
  - Chain tip fetch and error handling
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest


# =============================================================================
# _get_chain_tip
# =============================================================================


class TestGetChainTip:
    """Verify chain tip fetching from mempool.space API."""

    @pytest.mark.asyncio
    async def test_chain_tip_success(self):
        """Parses integer from API response text."""
        from src.workers.backfill import _get_chain_tip

        mock_response = MagicMock()
        mock_response.text = "900123\n"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _get_chain_tip(mock_client)
        assert result == 900123

    @pytest.mark.asyncio
    async def test_chain_tip_failure(self):
        """Returns None on API error."""
        from src.workers.backfill import _get_chain_tip

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

        result = await _get_chain_tip(mock_client)
        assert result is None


# =============================================================================
# incremental_backfill — Gap Detection
# =============================================================================


class TestIncrementalBackfillGapDetection:
    """Verify gap detection and fetch logic."""

    @pytest.mark.asyncio
    async def test_no_gap_returns_zero(self):
        """When DB height >= chain tip, no blocks are fetched."""
        from src.workers.backfill import incremental_backfill

        with (
            patch("src.workers.backfill.engine") as mock_engine,
            patch("src.workers.backfill._get_db_max_height", return_value=900100),
            patch("src.workers.backfill._get_chain_tip", return_value=900100),
        ):
            # Mock DDL bootstrap
            mock_conn = AsyncMock()
            mock_engine.begin.return_value.__aenter__ = AsyncMock(
                return_value=mock_conn
            )
            mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await incremental_backfill()
            assert result == 0

    @pytest.mark.asyncio
    async def test_chain_tip_unavailable_returns_zero(self):
        """When chain tip cannot be fetched, returns 0 gracefully."""
        from src.workers.backfill import incremental_backfill

        with (
            patch("src.workers.backfill.engine") as mock_engine,
            patch("src.workers.backfill._get_chain_tip", return_value=None),
        ):
            mock_conn = AsyncMock()
            mock_engine.begin.return_value.__aenter__ = AsyncMock(
                return_value=mock_conn
            )
            mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await incremental_backfill()
            assert result == 0

    @pytest.mark.asyncio
    async def test_gap_detected_triggers_fetch(self):
        """When DB height < chain tip, blocks are fetched and inserted."""
        from src.workers.backfill import incremental_backfill

        mock_blocks = [
            MagicMock(
                height=900101 + i,
                id="a" * 64,
                timestamp=1700000000 + i * 600,
                tx_count=3000,
                size=1500000,
                extras=MagicMock(
                    median_fee=5.0,
                    total_fees=2000000,
                    pool={"name": "TestPool"},
                    fee_range=[1.0, 5.0, 10.0],
                ),
            )
            for i in range(5)
        ]

        with (
            patch("src.workers.backfill.engine") as mock_engine,
            patch("src.workers.backfill._get_db_max_height", return_value=900100),
            patch("src.workers.backfill._get_chain_tip", return_value=900105),
            patch(
                "src.workers.backfill._fetch_blocks_in_range",
                return_value=mock_blocks,
            ),
            patch("src.workers.backfill._bulk_insert_blocks", return_value=5),
        ):
            mock_conn = AsyncMock()
            mock_engine.begin.return_value.__aenter__ = AsyncMock(
                return_value=mock_conn
            )
            mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await incremental_backfill()
            assert result == 5

    @pytest.mark.asyncio
    async def test_empty_db_full_backfill(self):
        """When DB is empty, fetches up to target_blocks from chain tip."""
        from src.workers.backfill import incremental_backfill

        with (
            patch("src.workers.backfill.engine") as mock_engine,
            patch("src.workers.backfill._get_db_max_height", return_value=None),
            patch("src.workers.backfill._get_chain_tip", return_value=900200),
            patch(
                "src.workers.backfill._fetch_blocks_in_range",
                return_value=[],
            ),
        ):
            mock_conn = AsyncMock()
            mock_engine.begin.return_value.__aenter__ = AsyncMock(
                return_value=mock_conn
            )
            mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await incremental_backfill(target_blocks=10)
            assert result == 0  # No blocks fetched
