from confluent_kafka import Producer
from src.config import settings

class MempoolProducer:
    """
    High-level Kafka producer wrapper for mempool data orchestration.
    """

    def __init__(self):
        """
        Initializes the Kafka producer using project settings.
        """
        conf = {
            'bootstrap.servers': settings.kafka_bootstrap_servers,
            'client.id': 'mempool-orchestrator-producer',
            'acks': 1
        }
        self.producer = Producer(conf)

    def produce(self, topic: str, key: str, value: bytes):
        """
        Asynchronously produces a message to a specific Kafka topic.

        Args:
            topic (str): The destination Kafka topic.
            key (str): Message key for partitioning logic.
            value (bytes): Encoded message payload.
        """
        try:
            self.producer.produce(
                topic=topic,
                key=key,
                value=value,
                callback=self._delivery_report
            )
            self.producer.poll(0)
        except Exception as e:
            print(f"CRITICAL: Kafka production error: {e}")

    def _delivery_report(self, err, msg):
        """
        Internal callback for message delivery reports.

        Args:
            err (KafkaError): Error object if delivery failed, else None.
            msg (Message): The delivered message object.
        """
        if err is not None:
            print(f"ERROR: Delivery failed: {err}")
        else:
            print(f"OK: {msg.key()} -> {msg.topic()} at offset {msg.offset()}")

    def flush(self):
        """
        Blocks until all messages in the producer queue are delivered.
        """
        self.producer.flush()