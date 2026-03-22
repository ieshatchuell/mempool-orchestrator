"""Block Fetcher worker — consumes block signals and fetches enriched block data.

ADR-024: I/O Decoupled Architecture.
Consumes lightweight block signals from the 'block-signals' Kafka topic,
fetches the full block data from the mempool.space REST API, and produces
the validated payload to 'mempool-raw' for downstream materialization.

Usage:
    cd backend && uv run python -m src.workers.block_fetcher
"""

import asyncio
import json

import httpx
from aiokafka import AIOKafkaConsumer
from loguru import logger
from pydantic import ValidationError

from src.core.config import settings
from src.infrastructure.messaging.producer import MempoolProducer
from src.domain.schemas import ConfirmedBlock

# Shared async HTTP client for block fetches
_http_client: httpx.AsyncClient | None = None


async def _get_http_client() -> httpx.AsyncClient:
    """Lazy singleton for the async HTTP client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30)
    return _http_client


async def fetch_confirmed_block(block_hash: str) -> ConfirmedBlock | None:
    """Fetch full block data from REST API and validate with Pydantic.

    Args:
        block_hash: The block hash from the signal payload.

    Returns:
        Validated ConfirmedBlock or None if fetch/validation fails.
    """
    url = f"{settings.mempool_api_url}/v1/block/{block_hash}"
    try:
        client = await _get_http_client()
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return ConfirmedBlock.model_validate(data)
    except httpx.HTTPStatusError as e:
        logger.error(f"REST API error fetching block {block_hash}: {e.response.status_code}")
    except ValidationError as e:
        logger.error(f"ConfirmedBlock validation failed for {block_hash}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching block {block_hash}: {e}")
    return None


async def handle_block_signal(value: bytes, producer: MempoolProducer) -> None:
    """Process a single block signal: fetch enriched data and produce to mempool-raw.

    Args:
        value: Raw Kafka message value (JSON: {"hash": str, "height": int}).
        producer: Started MempoolProducer instance.
    """
    try:
        signal = json.loads(value)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in block signal payload")
        return

    block_hash = signal.get("hash")
    block_height = signal.get("height")

    if not block_hash:
        logger.warning(f"Block signal missing 'hash' field: {signal}")
        return

    logger.info(f"Processing block signal: height={block_height}, hash={block_hash[:16]}...")

    confirmed = await fetch_confirmed_block(block_hash)

    if confirmed:
        await producer.send(
            key="confirmed_block",
            value=confirmed.model_dump_json().encode("utf-8"),
        )
        logger.info(
            f"ConfirmedBlock: height={confirmed.height}, "
            f"median_fee={confirmed.extras.median_fee:.2f} sat/vB, "
            f"tx_count={confirmed.tx_count}"
        )
    else:
        logger.warning(f"Could not fetch block details for {block_hash[:16]}...")


async def block_fetcher() -> None:
    """Main consumer loop for block signal processing."""
    # 1. Start Kafka producer (for publishing to mempool-raw)
    producer = MempoolProducer()
    await producer.start()

    # 2. Start Kafka consumer (for reading from block-signals)
    consumer = AIOKafkaConsumer(
        settings.block_signals_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="block-fetchers",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info(
        f"Block Fetcher consuming from '{settings.block_signals_topic}' "
        f"(group: block-fetchers)"
    )

    # 3. Consume loop with graceful shutdown
    try:
        async for msg in consumer:
            try:
                await handle_block_signal(msg.value, producer)
            except Exception as e:
                logger.error(f"Failed to process block signal: {e}", exc_info=True)
    finally:
        await consumer.stop()
        await producer.stop()
        if _http_client and not _http_client.is_closed:
            await _http_client.aclose()
        logger.info("Block Fetcher shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(block_fetcher())
