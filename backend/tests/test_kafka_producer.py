"""Unit tests for async Kafka producer wrapper.

Tests validate the MempoolProducer wrapper behavior using mocked
aiokafka.AIOKafkaProducer to avoid real Kafka connections.

Updated for Phase 5 EDA: async producer via aiokafka (replaces confluent-kafka).
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.infrastructure.messaging.producer import MempoolProducer


class TestMempoolProducerLifecycle:
    """Test suite for MempoolProducer lifecycle management."""

    def test_producer_initial_state(self):
        """Verify producer starts with no underlying connection."""
        producer = MempoolProducer()
        assert producer._producer is None

    @pytest.mark.asyncio
    async def test_start_creates_producer(self):
        """Verify start() initializes and starts the aiokafka producer."""
        producer = MempoolProducer()

        with patch("src.infrastructure.messaging.producer.AIOKafkaProducer") as MockProducer:
            mock_instance = AsyncMock()
            MockProducer.return_value = mock_instance

            await producer.start()

            MockProducer.assert_called_once()
            mock_instance.start.assert_called_once()
            assert producer._producer is mock_instance

    @pytest.mark.asyncio
    async def test_stop_closes_producer(self):
        """Verify stop() flushes and closes the producer."""
        producer = MempoolProducer()

        with patch("src.infrastructure.messaging.producer.AIOKafkaProducer") as MockProducer:
            mock_instance = AsyncMock()
            MockProducer.return_value = mock_instance

            await producer.start()
            await producer.stop()

            mock_instance.stop.assert_called_once()
            assert producer._producer is None

    @pytest.mark.asyncio
    async def test_stop_noop_when_not_started(self):
        """Verify stop() is a no-op when producer was never started."""
        producer = MempoolProducer()
        await producer.stop()  # Should not raise
        assert producer._producer is None


class TestSendMethod:
    """Test suite for the send() method."""

    @pytest.mark.asyncio
    async def test_send_calls_send_and_wait(self):
        """Verify send() calls the underlying send_and_wait with correct args."""
        producer = MempoolProducer()

        with patch("src.infrastructure.messaging.producer.AIOKafkaProducer") as MockProducer:
            mock_instance = AsyncMock()
            MockProducer.return_value = mock_instance

            await producer.start()
            await producer.send(key="stats", value=b'{"data": "test"}')

            mock_instance.send_and_wait.assert_called_once()
            call_kwargs = mock_instance.send_and_wait.call_args.kwargs
            assert call_kwargs["key"] == b"stats"  # Encoded to bytes
            assert call_kwargs["value"] == b'{"data": "test"}'

    @pytest.mark.asyncio
    async def test_send_raises_when_not_started(self):
        """Verify send() raises RuntimeError if producer not started."""
        producer = MempoolProducer()

        with pytest.raises(RuntimeError, match="Producer not started"):
            await producer.send(key="test", value=b"data")

    @pytest.mark.asyncio
    async def test_multiple_sends(self):
        """Verify multiple send() calls work correctly."""
        producer = MempoolProducer()

        with patch("src.infrastructure.messaging.producer.AIOKafkaProducer") as MockProducer:
            mock_instance = AsyncMock()
            MockProducer.return_value = mock_instance

            await producer.start()
            await producer.send(key="stats", value=b"payload1")
            await producer.send(key="confirmed_block", value=b"payload2")
            await producer.send(key="mempool_block", value=b"payload3")

            assert mock_instance.send_and_wait.call_count == 3
