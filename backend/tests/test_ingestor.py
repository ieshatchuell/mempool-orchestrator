"""Unit tests for WebSocket ingestor routing logic.

Tests verify the route_message function correctly routes different event types
to Kafka with proper validation using mocked async producers.

Updated for Phase 5 EDA: imports from src.workers.ingestor,
producer uses async .send() instead of sync .produce().
"""

import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from src.workers.ingestor import route_message


class TestRouteMessage:
    """Test suite for message routing logic with mocked async Kafka producer."""

    @pytest.mark.asyncio
    async def test_route_stats(self):
        """Verify stats events are routed with key='stats'."""
        mock_producer = AsyncMock()

        data = {
            "mempoolInfo": {
                "size": 150000,
                "bytes": 75000000,
                "usage": 250000000,
                "totalFee": 1.5,
                "mempoolMinFee": 0.00001,
                "minRelayTxFee": 0.00001
            }
        }

        await route_message(data, mock_producer)

        assert mock_producer.send.call_count == 1
        call_kwargs = mock_producer.send.call_args.kwargs
        assert call_kwargs["key"] == "stats"
        assert "value" in call_kwargs

    @pytest.mark.asyncio
    async def test_route_blocks(self):
        """Verify mempool-blocks events are routed with key='mempool_block'."""
        mock_producer = AsyncMock()

        data = {
            "mempool-blocks": [
                {
                    "blockSize": 1500000,
                    "blockVSize": 999817,
                    "nTx": 2500,
                    "totalFees": 50000000,
                    "medianFee": 15.5,
                    "feeRange": [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0]
                },
                {
                    "blockSize": 1400000,
                    "blockVSize": 950000,
                    "nTx": 2300,
                    "totalFees": 45000000,
                    "medianFee": 14.0,
                    "feeRange": [1.0, 4.0, 9.0, 14.0, 19.0, 28.0, 48.0, 95.0]
                }
            ]
        }

        await route_message(data, mock_producer)

        assert mock_producer.send.call_count == 1
        call_kwargs = mock_producer.send.call_args.kwargs
        assert call_kwargs["key"] == "mempool_block"
        assert "value" in call_kwargs

    @pytest.mark.asyncio
    async def test_ignore_conversions(self):
        """Verify conversions messages are silently ignored (no Kafka produce)."""
        mock_producer = AsyncMock()

        data = {
            "conversions": {
                "USD": 95000.50,
                "EUR": 88000.00,
                "GBP": 75000.00
            }
        }

        await route_message(data, mock_producer)

        mock_producer.send.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.workers.ingestor.fetch_confirmed_block")
    async def test_route_confirmed_block(self, mock_fetch):
        """Verify confirmed block signals trigger Signal & Fetch and produce to Kafka."""
        mock_producer = AsyncMock()

        # Mock the REST API fetch to return a valid ConfirmedBlock
        from src.domain.schemas import ConfirmedBlock, ConfirmedBlockExtras
        mock_block = ConfirmedBlock(
            id="00000000000000000001abcdef",
            height=800000,
            timestamp=1706500000,
            size=1500000,
            tx_count=3000,
            extras=ConfirmedBlockExtras(
                virtual_size=997892.5,
                total_fees=2036508,
                median_fee=5.0,
                fee_range=[1.0, 2.0, 5.0, 10.0],
                pool={"name": "Foundry USA"}
            )
        )
        mock_fetch.return_value = mock_block

        data = {
            "block": {
                "id": "00000000000000000001abcdef",
                "height": 800000,
                "timestamp": 1706500000,
                "tx_count": 3000,
                "size": 1500000,
                "weight": 4000000
            }
        }

        await route_message(data, mock_producer)

        # Assert fetch was called with the block hash
        mock_fetch.assert_called_once_with("00000000000000000001abcdef")

        # Assert producer.send was called with confirmed_block key
        assert mock_producer.send.call_count == 1
        call_kwargs = mock_producer.send.call_args.kwargs
        assert call_kwargs["key"] == "confirmed_block"

    @pytest.mark.asyncio
    @patch("src.workers.ingestor.fetch_confirmed_block")
    async def test_confirmed_block_fetch_failure(self, mock_fetch):
        """Verify that if REST fetch fails, no message is produced."""
        mock_producer = AsyncMock()
        mock_fetch.return_value = None  # Fetch failed

        data = {
            "block": {
                "id": "00000000000000000001234567890abcdef",
                "height": 800000,
                "timestamp": 1706500000,
                "tx_count": 3000,
                "size": 1500000,
                "weight": 4000000
            }
        }

        await route_message(data, mock_producer)

        mock_fetch.assert_called_once()
        mock_producer.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_validation_error_invalid_stats(self):
        """Verify validation errors don't produce to Kafka."""
        mock_producer = AsyncMock()

        data = {
            "mempoolInfo": {
                "size": "invalid_string",  # Invalid type
                "bytes": 75000000,
                "totalFee": 1.5
            }
        }

        await route_message(data, mock_producer)

        mock_producer.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_validation_error_invalid_block(self):
        """Verify invalid block data doesn't produce to Kafka."""
        mock_producer = AsyncMock()

        data = {
            "mempool-blocks": [
                {
                    "blockSize": 1500000,
                    "blockVSize": 999817,
                    "nTx": 2500,
                    "totalFees": "bad_value",  # Invalid type
                    "medianFee": 15.5,
                    "feeRange": [1.0, 5.0, 10.0]
                }
            ]
        }

        await route_message(data, mock_producer)

        mock_producer.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_block_validation(self):
        """Verify that valid blocks are produced even if some blocks fail validation."""
        mock_producer = AsyncMock()

        data = {
            "mempool-blocks": [
                # Valid block
                {
                    "blockSize": 1500000,
                    "blockVSize": 999817,
                    "nTx": 2500,
                    "totalFees": 50000000,
                    "medianFee": 15.5,
                    "feeRange": [1.0, 5.0, 10.0]
                },
                # Invalid block (missing required field)
                {
                    "blockSize": 1400000,
                    "blockVSize": 950000,
                    "nTx": 2300,
                    "totalFees": 45000000,
                    # medianFee missing
                    "feeRange": [1.0, 4.0, 9.0]
                }
            ]
        }

        await route_message(data, mock_producer)

        assert mock_producer.send.call_count == 1
        call_kwargs = mock_producer.send.call_args.kwargs
        assert call_kwargs["key"] == "mempool_block"

    @pytest.mark.asyncio
    async def test_unknown_message_type(self):
        """Verify unknown message types are ignored."""
        mock_producer = AsyncMock()

        data = {
            "unknown_key": {
                "some": "data"
            }
        }

        await route_message(data, mock_producer)

        mock_producer.send.assert_not_called()
