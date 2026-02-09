"""Unit tests for WebSocket ingestor routing logic.

Tests verify the route_message function correctly routes different event types
to Kafka with proper validation using mocked producers.
"""

from unittest.mock import MagicMock, call
import pytest

from src.ingestors.mempool_ws import route_message


class TestRouteMessage:
    """Test suite for message routing logic with mocked Kafka producer."""

    def test_route_stats(self):
        """Verify stats events are routed with key='stats'."""
        # Mock producer
        mock_producer = MagicMock()
        
        # Valid stats payload from WebSocket
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
        
        # Route the message
        route_message(data, mock_producer)
        
        # Assert producer.produce was called exactly once
        assert mock_producer.produce.call_count == 1
        
        # Verify it was called with correct key
        call_kwargs = mock_producer.produce.call_args.kwargs
        assert call_kwargs["key"] == "stats"
        assert "value" in call_kwargs

    def test_route_blocks(self):
        """Verify mempool-blocks events are routed with key='mempool_block'."""
        # Mock producer
        mock_producer = MagicMock()
        
        # Valid mempool-blocks payload from WebSocket
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
        
        # Route the message
        route_message(data, mock_producer)
        
        # Assert producer.produce was called exactly once
        assert mock_producer.produce.call_count == 1
        
        # Verify it was called with correct key
        call_kwargs = mock_producer.produce.call_args.kwargs
        assert call_kwargs["key"] == "mempool_block"
        assert "value" in call_kwargs

    def test_route_blocks_alternative_format(self):
        """Verify blocks with 'blocks' key (alternative format) are routed correctly."""
        # Mock producer
        mock_producer = MagicMock()
        
        # Alternative format with "blocks" key
        data = {
            "blocks": [
                {
                    "blockSize": 1200000,
                    "blockVSize": 800000,
                    "nTx": 2000,
                    "totalFees": 40000000,
                    "medianFee": 12.5,
                    "feeRange": [1.0, 3.0, 8.0, 12.0]
                }
            ]
        }
        
        # Route the message
        route_message(data, mock_producer)
        
        # Assert producer.produce was called
        assert mock_producer.produce.call_count == 1
        call_kwargs = mock_producer.produce.call_args.kwargs
        assert call_kwargs["key"] == "mempool_block"

    def test_ignore_conversions(self):
        """Verify conversions messages are silently ignored (no Kafka produce)."""
        # Mock producer
        mock_producer = MagicMock()
        
        # Conversions payload (initialization noise)
        data = {
            "conversions": {
                "USD": 95000.50,
                "EUR": 88000.00,
                "GBP": 75000.00
            }
        }
        
        # Route the message
        route_message(data, mock_producer)
        
        # Assert producer.produce was NOT called
        mock_producer.produce.assert_not_called()

    def test_ignore_block_signal(self):
        """Verify confirmed block signals are logged but not produced to Kafka."""
        # Mock producer
        mock_producer = MagicMock()
        
        # Confirmed block signal (future feature)
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
        
        # Route the message
        route_message(data, mock_producer)
        
        # Assert producer.produce was NOT called (block signals not processed yet)
        mock_producer.produce.assert_not_called()

    def test_validation_error_invalid_stats(self):
        """Verify validation errors don't produce to Kafka."""
        # Mock producer
        mock_producer = MagicMock()
        
        # Invalid stats: size should be int, but we pass string
        data = {
            "mempoolInfo": {
                "size": "invalid_string",  # Invalid type
                "bytes": 75000000,
                "totalFee": 1.5
            }
        }
        
        # Route the message (should catch ValidationError internally)
        route_message(data, mock_producer)
        
        # Assert producer.produce was NOT called due to validation error
        mock_producer.produce.assert_not_called()

    def test_validation_error_invalid_block(self):
        """Verify invalid block data doesn't produce to Kafka."""
        # Mock producer
        mock_producer = MagicMock()
        
        # Invalid block: totalFees should be int
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
        
        # Route the message
        route_message(data, mock_producer)
        
        # Assert producer.produce was NOT called (all blocks failed validation)
        mock_producer.produce.assert_not_called()

    def test_partial_block_validation(self):
        """Verify that valid blocks are produced even if some blocks fail validation."""
        # Mock producer
        mock_producer = MagicMock()
        
        # Mix of valid and invalid blocks
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
        
        # Route the message
        route_message(data, mock_producer)
        
        # Assert producer.produce was called once (for the valid block)
        assert mock_producer.produce.call_count == 1
        call_kwargs = mock_producer.produce.call_args.kwargs
        assert call_kwargs["key"] == "mempool_block"

    def test_unknown_message_type(self):
        """Verify unknown message types are ignored."""
        # Mock producer
        mock_producer = MagicMock()
        
        # Unknown message structure
        data = {
            "unknown_key": {
                "some": "data"
            }
        }
        
        # Route the message
        route_message(data, mock_producer)
        
        # Assert producer.produce was NOT called
        mock_producer.produce.assert_not_called()
