"""Unit tests for Kafka producer wrapper.

Tests validate the MempoolProducer wrapper behavior using mocked
confluent_kafka.Producer to avoid real Kafka connections.
"""

from unittest.mock import MagicMock, patch, call
import pytest

from src.common.kafka_producer import MempoolProducer


class TestMempoolProducerInitialization:
    """Test suite for MempoolProducer initialization."""

    @patch('src.common.kafka_producer.Producer')
    def test_producer_initialized_with_correct_config(self, mock_producer_class):
        """Verify Producer is initialized with correct configuration."""
        # Create MempoolProducer (should instantiate confluent_kafka.Producer)
        producer = MempoolProducer()
        
        # Assert Producer was called once
        mock_producer_class.assert_called_once()
        
        # Verify config passed to Producer
        call_args = mock_producer_class.call_args[0][0]  # First positional arg (config dict)
        assert call_args['bootstrap.servers'] == 'localhost:9092'  # default from settings
        assert call_args['client.id'] == 'mempool-orchestrator-producer'
        assert call_args['acks'] == 1

    @patch('src.common.kafka_producer.Producer')
    def test_producer_instance_stored(self, mock_producer_class):
        """Verify the underlying Producer instance is stored."""
        mock_instance = MagicMock()
        mock_producer_class.return_value = mock_instance
        
        producer = MempoolProducer()
        
        # Assert producer.producer is the mocked Producer instance
        assert producer.producer is mock_instance


class TestProduceMethod:
    """Test suite for the produce() method."""

    @patch('src.common.kafka_producer.Producer')
    def test_produce_calls_underlying_producer(self, mock_producer_class):
        """Verify produce() calls the underlying Kafka producer correctly."""
        # Setup mock
        mock_instance = MagicMock()
        mock_producer_class.return_value = mock_instance
        
        producer = MempoolProducer()
        
        # Call produce
        test_topic = "test-topic"
        test_key = "test-key"
        test_value = b'{"data": "test"}'
        
        producer.produce(topic=test_topic, key=test_key, value=test_value)
        
        # Assert underlying producer.produce was called
        mock_instance.produce.assert_called_once_with(
            topic=test_topic,
            key=test_key,
            value=test_value,
            callback=producer._delivery_report  # Should pass the callback
        )

    @patch('src.common.kafka_producer.Producer')
    def test_produce_calls_poll_after_produce(self, mock_producer_class):
        """Verify produce() calls poll(0) for non-blocking delivery report handling."""
        mock_instance = MagicMock()
        mock_producer_class.return_value = mock_instance
        
        producer = MempoolProducer()
        producer.produce(topic="test", key="key", value=b"value")
        
        # Assert poll(0) was called after produce
        mock_instance.poll.assert_called_once_with(0)

    @patch('src.common.kafka_producer.Producer')
    @patch('builtins.print')
    def test_produce_handles_exception(self, mock_print, mock_producer_class):
        """Verify produce() catches and logs exceptions from underlying producer."""
        mock_instance = MagicMock()
        mock_instance.produce.side_effect = Exception("Kafka connection error")
        mock_producer_class.return_value = mock_instance
        
        producer = MempoolProducer()
        
        # Should not raise, but should log error
        producer.produce(topic="test", key="key", value=b"value")
        
        # Verify error was printed
        mock_print.assert_called_once()
        assert "CRITICAL: Kafka production error" in mock_print.call_args[0][0]
        assert "Kafka connection error" in mock_print.call_args[0][0]


class TestDeliveryReportCallback:
    """Test suite for _delivery_report callback."""

    @patch('src.common.kafka_producer.Producer')
    @patch('builtins.print')
    def test_delivery_report_success(self, mock_print, mock_producer_class):
        """Verify _delivery_report logs success when err is None."""
        producer = MempoolProducer()
        
        # Mock successful message delivery
        mock_msg = MagicMock()
        mock_msg.key.return_value = b"stats"
        mock_msg.topic.return_value = "mempool-raw"
        mock_msg.offset.return_value = 12345
        
        # Call callback with err=None (success)
        producer._delivery_report(err=None, msg=mock_msg)
        
        # Verify success was logged
        mock_print.assert_called_once()
        log_output = mock_print.call_args[0][0]
        assert "OK:" in log_output
        assert "stats" in log_output
        assert "mempool-raw" in log_output
        assert "12345" in log_output

    @patch('src.common.kafka_producer.Producer')
    @patch('builtins.print')
    def test_delivery_report_failure(self, mock_print, mock_producer_class):
        """Verify _delivery_report logs error when err is not None."""
        producer = MempoolProducer()
        
        # Mock failed message delivery
        mock_err = MagicMock()
        mock_err.__str__ = lambda self: "Broker not available"
        mock_msg = MagicMock()
        
        # Call callback with err object (failure)
        producer._delivery_report(err=mock_err, msg=mock_msg)
        
        # Verify error was logged
        mock_print.assert_called_once()
        log_output = mock_print.call_args[0][0]
        assert "ERROR: Delivery failed" in log_output

    @patch('src.common.kafka_producer.Producer')
    def test_delivery_report_called_with_correct_signature(self, mock_producer_class):
        """Verify _delivery_report callback has the correct signature for Kafka."""
        producer = MempoolProducer()
        
        # Verify the callback exists and is callable
        assert callable(producer._delivery_report)
        
        # Verify it accepts err and msg parameters
        import inspect
        sig = inspect.signature(producer._delivery_report)
        params = list(sig.parameters.keys())
        assert 'err' in params
        assert 'msg' in params


class TestFlushMethod:
    """Test suite for the flush() method."""

    @patch('src.common.kafka_producer.Producer')
    def test_flush_calls_underlying_flush(self, mock_producer_class):
        """Verify flush() calls the underlying producer's flush method."""
        mock_instance = MagicMock()
        mock_producer_class.return_value = mock_instance
        
        producer = MempoolProducer()
        producer.flush()
        
        # Assert underlying flush was called
        mock_instance.flush.assert_called_once()

    @patch('src.common.kafka_producer.Producer')
    def test_flush_blocks_until_delivery(self, mock_producer_class):
        """Verify flush() is a blocking operation (integration behavior)."""
        mock_instance = MagicMock()
        mock_producer_class.return_value = mock_instance
        
        producer = MempoolProducer()
        
        # Produce multiple messages
        producer.produce("topic", "key1", b"value1")
        producer.produce("topic", "key2", b"value2")
        
        # Flush should be called once
        producer.flush()
        mock_instance.flush.assert_called_once()


class TestIntegrationScenarios:
    """Test suite for realistic usage scenarios."""

    @patch('src.common.kafka_producer.Producer')
    def test_multiple_produce_calls(self, mock_producer_class):
        """Verify multiple produce calls work correctly."""
        mock_instance = MagicMock()
        mock_producer_class.return_value = mock_instance
        
        producer = MempoolProducer()
        
        # Produce multiple messages
        producer.produce("topic", "stats", b'{"size": 1000}')
        producer.produce("topic", "mempool_block", b'{"blockSize": 500000}')
        
        # Verify both calls went through
        assert mock_instance.produce.call_count == 2
        assert mock_instance.poll.call_count == 2

    @patch('src.common.kafka_producer.Producer')
    @patch('builtins.print')
    def test_partial_failure_doesnt_crash(self, mock_print, mock_producer_class):
        """Verify one failed produce doesn't prevent subsequent produces."""
        mock_instance = MagicMock()
        
        # First call fails, second succeeds
        mock_instance.produce.side_effect = [
            Exception("Network error"),
            None  # Success
        ]
        mock_producer_class.return_value = mock_instance
        
        producer = MempoolProducer()
        
        # First produce fails
        producer.produce("topic", "key1", b"value1")
        
        # Second produce should still work
        producer.produce("topic", "key2", b"value2")
        
        # Verify both attempts were made
        assert mock_instance.produce.call_count == 2
        
        # Verify error was logged for first attempt
        assert mock_print.call_count == 1
        assert "CRITICAL" in mock_print.call_args[0][0]
