"""Async Kafka producer for event publishing via Redpanda.

Wraps aiokafka.AIOKafkaProducer with lifecycle management.
Topic and bootstrap servers sourced from settings — zero magic strings.
"""

from loguru import logger
from aiokafka import AIOKafkaProducer

from src.core.config import settings


class MempoolProducer:
    """Async Kafka producer with managed lifecycle.

    Usage:
        producer = MempoolProducer()
        await producer.start()
        await producer.send(key="stats", value=payload_bytes)
        await producer.stop()
    """

    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Initialize and start the Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
        )
        await self._producer.start()
        logger.info(f"🟢 Kafka producer connected to {settings.kafka_bootstrap_servers}")

    async def send(self, key: str, value: bytes) -> None:
        """Produce a message to the configured mempool topic.

        Args:
            key: Message key for partition routing (e.g. 'stats', 'confirmed_block').
            value: Serialized message payload (bytes).
        """
        if self._producer is None:
            raise RuntimeError("Producer not started. Call start() first.")

        await self._producer.send_and_wait(
            topic=settings.mempool_topic,
            key=key.encode("utf-8"),
            value=value,
        )

    async def stop(self) -> None:
        """Flush pending messages and close the producer."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("🔴 Kafka producer stopped.")
