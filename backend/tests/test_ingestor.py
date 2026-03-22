"""Unit tests for WebSocket ingestor routing logic.

Tests verify the route_message function correctly routes different event types
to Kafka with proper validation using mocked async producers.

Updated for ADR-024: Block events now produce signals to block-signals topic
instead of performing REST fetches inline.
"""

import json
from unittest.mock import AsyncMock

import pytest

from src.core.config import settings
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
    async def test_block_signal_published_to_block_signals(self):
        """ADR-024: Block events produce a signal to block-signals topic."""
        mock_producer = AsyncMock()

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

        # Assert producer.send was called once with block_signal key
        assert mock_producer.send.call_count == 1
        call_kwargs = mock_producer.send.call_args.kwargs
        assert call_kwargs["key"] == "block_signal"
        assert call_kwargs["topic"] == settings.block_signals_topic

        # Verify payload contains hash and height
        payload = json.loads(call_kwargs["value"].decode("utf-8"))
        assert payload["hash"] == "00000000000000000001abcdef"
        assert payload["height"] == 800000

    @pytest.mark.asyncio
    async def test_block_signal_missing_hash(self):
        """Block signal without hash does not produce to Kafka."""
        mock_producer = AsyncMock()

        data = {
            "block": {
                "height": 800000,
                "timestamp": 1706500000,
            }
        }

        await route_message(data, mock_producer)

        # No hash → no signal produced, but handled flag is True (no unknown warning)
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

    # ── ADR-021: Fee Enrichment Tests ────────────────────────────

    @pytest.mark.asyncio
    async def test_enrichment_injects_median_fee(self):
        """ADR-021: medianFee from mempool-blocks[0] is injected into stats payload."""
        mock_producer = AsyncMock()

        data = {
            "mempoolInfo": {
                "size": 150000,
                "bytes": 75000000,
                "usage": 250000000,
                "totalFee": 1.5,
                "mempoolMinFee": 0.00001,
                "minRelayTxFee": 0.00001,
            },
            "mempool-blocks": [
                {
                    "blockSize": 1500000,
                    "blockVSize": 999817,
                    "nTx": 2500,
                    "totalFees": 50000000,
                    "medianFee": 8.5,
                    "feeRange": [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0],
                },
            ],
        }

        await route_message(data, mock_producer)

        # Stats should be produced
        stats_calls = [
            c for c in mock_producer.send.call_args_list
            if c.kwargs.get("key") == "stats"
        ]
        assert len(stats_calls) == 1

        # Verify the serialized payload contains the enriched median_fee
        payload = json.loads(stats_calls[0].kwargs["value"].decode("utf-8"))
        assert payload["mempool_info"]["median_fee"] == 8.5

    @pytest.mark.asyncio
    async def test_enrichment_fallback_empty_blocks(self):
        """ADR-021: when no mempool-blocks exist, medianFee defaults to 1.0."""
        mock_producer = AsyncMock()

        data = {
            "mempoolInfo": {
                "size": 50000,
                "bytes": 25000000,
                "usage": 100000000,
                "totalFee": 0.5,
                "mempoolMinFee": 0.00001,
                "minRelayTxFee": 0.00001,
            },
            # No "mempool-blocks" key at all
        }

        await route_message(data, mock_producer)

        stats_calls = [
            c for c in mock_producer.send.call_args_list
            if c.kwargs.get("key") == "stats"
        ]
        assert len(stats_calls) == 1

        payload = json.loads(stats_calls[0].kwargs["value"].decode("utf-8"))
        assert payload["mempool_info"]["median_fee"] == 1.0
