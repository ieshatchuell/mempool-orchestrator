import json
from confluent_kafka import Producer

class MempoolProducer:
    """
    Infrastructure client for Redpanda/Kafka interaction.
    Handles message serialization and delivery reports.
    """
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'mempool-orchestrator-ingestor',
            'acks': 1  # Standard durability for ingestion
        }
        self.producer = Producer(self.config)

    def delivery_report(self, err, msg):
        """
        Callback executed on message delivery or failure.
        """
        if err is not None:
            print(f"Delivery failed for record {msg.key()}: {err}")
        else:
            print(f"Record {msg.key()} successfully produced to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    def produce(self, topic: str, key: str, value: dict):
        """
        Asynchronously sends a dictionary payload to a Kafka topic.
        """
        try:
            payload = json.dumps(value).encode('utf-8')
            self.producer.produce(
                topic, 
                key=key, 
                value=payload, 
                on_delivery=self.delivery_report
            )
            # Trigger delivery reports for queued messages
            self.producer.poll(0)
        except Exception as e:
            print(f"Critical error in producer: {e}")

    def flush(self):
        """
        Ensures all messages in the buffer are delivered before shutdown.
        """
        self.producer.flush()