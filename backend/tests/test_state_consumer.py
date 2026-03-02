"""Unit tests for State Consumer — ORM models and materialization logic.

Tests cover:
  - BlockRecord new fields (pool_name, fee_range JSONB)
  - MempoolBlockProjection instantiation
  - JSONB serialization round-trips
  - Snapshot pattern (DELETE + INSERT) for mempool_block handler
"""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.infrastructure.database.models import BlockRecord, MempoolBlockProjection


# =============================================================================
# BlockRecord — New Fields
# =============================================================================


class TestBlockRecordNewFields:
    """Verify BlockRecord accepts the new pool_name and fee_range columns."""

    def test_block_record_accepts_pool_name(self):
        """BlockRecord instantiates correctly with a pool_name value."""
        record = BlockRecord(
            height=900000,
            hash="0" * 64,
            timestamp=1700000000,
            tx_count=3000,
            size=1500000,
            median_fee=5.0,
            total_fees=2000000,
            pool_name="Foundry USA",
        )
        assert record.pool_name == "Foundry USA"

    def test_block_record_pool_name_optional(self):
        """BlockRecord accepts pool_name=None (nullable field)."""
        record = BlockRecord(
            height=900001,
            hash="1" * 64,
            timestamp=1700000060,
            tx_count=2500,
            size=1400000,
            median_fee=4.0,
            total_fees=1800000,
            pool_name=None,
        )
        assert record.pool_name is None


# =============================================================================
# fee_range — JSONB Serialization
# =============================================================================


class TestFeeRangeJsonb:
    """Verify fee_range JSONB column handles Python lists correctly."""

    def test_fee_range_jsonb_roundtrip(self):
        """A list of floats assigned to fee_range is preserved as-is."""
        fee_data = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 178.72]
        record = BlockRecord(
            height=900002,
            hash="2" * 64,
            timestamp=1700000120,
            tx_count=3500,
            size=1600000,
            median_fee=10.0,
            total_fees=3000000,
            fee_range=fee_data,
        )
        assert record.fee_range == fee_data
        assert isinstance(record.fee_range, list)
        assert len(record.fee_range) == 7

    def test_fee_range_empty_list(self):
        """An empty list is a valid JSONB value."""
        record = BlockRecord(
            height=900003,
            hash="3" * 64,
            timestamp=1700000180,
            tx_count=100,
            size=50000,
            median_fee=1.0,
            total_fees=50000,
            fee_range=[],
        )
        assert record.fee_range == []

    def test_fee_range_none(self):
        """fee_range=None is accepted (nullable JSONB)."""
        record = BlockRecord(
            height=900004,
            hash="4" * 64,
            timestamp=1700000240,
            tx_count=200,
            size=100000,
            median_fee=2.0,
            total_fees=100000,
            fee_range=None,
        )
        assert record.fee_range is None


# =============================================================================
# MempoolBlockProjection — Model Instantiation
# =============================================================================


class TestMempoolBlockProjection:
    """Verify MempoolBlockProjection ORM model instantiates correctly."""

    def test_projection_model_instantiation(self):
        """MempoolBlockProjection creates a valid instance with all fields."""
        projection = MempoolBlockProjection(
            block_index=0,
            block_size=1500000,
            block_v_size=997892.5,
            n_tx=3000,
            total_fees=2000000,
            median_fee=5.0,
            fee_range=[0.14, 0.14, 0.15, 1.20, 2.29, 3.29, 178.72],
        )
        assert projection.block_index == 0
        assert projection.block_v_size == 997892.5  # Float, per ADR-003
        assert projection.n_tx == 3000
        assert isinstance(projection.fee_range, list)
        assert len(projection.fee_range) == 7


# =============================================================================
# Snapshot Pattern — _handle_mempool_block Logic
# =============================================================================


class TestHandleMempoolBlockSnapshot:
    """Verify the Snapshot (DELETE + INSERT) pattern in _handle_mempool_block."""

    @pytest.mark.asyncio
    async def test_handle_mempool_block_snapshot(self):
        """_handle_mempool_block deletes old projections and inserts new ones."""
        from src.workers.state_consumer import _handle_mempool_block

        # Build a valid mempool_block Kafka payload (JSON array)
        blocks_payload = json.dumps([
            {
                "blockSize": 1500000,
                "blockVSize": 997892.5,
                "nTx": 3000,
                "totalFees": 2000000,
                "medianFee": 5.0,
                "feeRange": [1.0, 2.0, 5.0, 10.0],
            },
            {
                "blockSize": 1400000,
                "blockVSize": 950000.0,
                "nTx": 2500,
                "totalFees": 1800000,
                "medianFee": 4.0,
                "feeRange": [0.5, 1.0, 3.0, 8.0],
            },
        ]).encode("utf-8")

        # Mock the async_session context manager
        mock_session = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.workers.state_consumer.async_session", return_value=mock_ctx):
            await _handle_mempool_block(blocks_payload)

        # Verify DELETE was called (truncate old projections)
        mock_session.execute.assert_called()

        # Verify session.add was called twice (2 blocks)
        assert mock_session.add.call_count == 2

        # Verify commit was called
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_mempool_block_block_index(self):
        """Block index matches enumeration order (0, 1, 2...)."""
        from src.workers.state_consumer import _handle_mempool_block

        blocks_payload = json.dumps([
            {
                "blockSize": 1500000,
                "blockVSize": 997892.5,
                "nTx": 3000,
                "totalFees": 2000000,
                "medianFee": 5.0,
                "feeRange": [1.0, 5.0],
            },
            {
                "blockSize": 1400000,
                "blockVSize": 950000.0,
                "nTx": 2500,
                "totalFees": 1800000,
                "medianFee": 4.0,
                "feeRange": [0.5, 3.0],
            },
            {
                "blockSize": 1300000,
                "blockVSize": 900000.0,
                "nTx": 2000,
                "totalFees": 1500000,
                "medianFee": 3.0,
                "feeRange": [0.1, 2.0],
            },
        ]).encode("utf-8")

        added_projections: list[MempoolBlockProjection] = []

        mock_session = AsyncMock()
        mock_session.add = MagicMock(side_effect=lambda p: added_projections.append(p))
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.workers.state_consumer.async_session", return_value=mock_ctx):
            await _handle_mempool_block(blocks_payload)

        # Verify block_index matches enumeration order
        assert len(added_projections) == 3
        assert added_projections[0].block_index == 0
        assert added_projections[1].block_index == 1
        assert added_projections[2].block_index == 2

        # Verify data integrity
        assert added_projections[0].block_v_size == 997892.5
        assert added_projections[2].n_tx == 2000
