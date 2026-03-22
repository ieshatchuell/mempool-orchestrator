"""Radar ingestion worker — real-time mempool stats, projected blocks, and block signals.

Connects to Mempool.space WebSocket API and streams validated events to Kafka (Redpanda)
via the async MempoolProducer.

Block events use the Signal-Only pattern (ADR-024):
1. WebSocket sends a block signal (hash, height)
2. Ingestor publishes the signal to 'block-signals' topic immediately
3. A separate block_fetcher worker handles the REST fetch asynchronously
"""

import asyncio
import json
from typing import Any

import websockets
from loguru import logger
from pydantic import ValidationError

from src.core.config import settings
from src.infrastructure.messaging.producer import MempoolProducer
from src.domain.schemas import MempoolStats, MempoolBlock


async def route_message(data: dict[str, Any], producer: MempoolProducer) -> None:
    """Route incoming WebSocket message to appropriate handler with Pydantic validation.

    Args:
        data: Decoded JSON payload from WebSocket.
        producer: Async Kafka producer instance (must be started).
    """
    # 1. Silence Noise (Initialization & UI data)
    ignored_keys = {"conversions", "loadingIndicators", "init"}
    if any(key in data for key in ignored_keys):
        return

    handled = False

    try:
        # Event Type 1: Mempool Stats (with ADR-021 fee enrichment)
        if "mempoolInfo" in data:
            # ADR-021: Enrich mempoolInfo with market median fee
            # The WebSocket mempoolInfo lacks medianFee. We extract it
            # from mempool-blocks[0] (the next block to be mined), which
            # represents the real market price for immediate confirmation.
            blocks_data = data.get("mempool-blocks", [])
            if isinstance(blocks_data, list) and len(blocks_data) > 0:
                block_0 = blocks_data[0]
                market_fee = block_0.get("medianFee", 1.0)
            else:
                market_fee = 1.0  # Fallback: MinRelayTxFee

            data["mempoolInfo"]["medianFee"] = market_fee

            stats = MempoolStats.model_validate(data)
            await producer.send(
                key="stats",
                value=stats.model_dump_json().encode("utf-8"),
            )
            logger.info(
                f"MempoolStats: size={stats.mempool_info.size}, "
                f"bytes={stats.mempool_info.bytes}, "
                f"median_fee={stats.mempool_info.median_fee:.2f} sat/vB"
            )
            handled = True

        # Event Type 2: Mempool Blocks (projected blocks)
        if "mempool-blocks" in data:
            blocks_data = data.get("mempool-blocks", [])

            if isinstance(blocks_data, list):
                validated_blocks: list[dict[str, Any]] = []
                for block_data in blocks_data:
                    try:
                        block = MempoolBlock.model_validate(block_data)
                        validated_blocks.append(block.model_dump())
                    except ValidationError as e:
                        logger.error(f"MempoolBlock validation failed: {e}")
                        continue

                if validated_blocks:
                    await producer.send(
                        key="mempool_block",
                        value=json.dumps(validated_blocks).encode("utf-8"),
                    )
                    logger.info(f"MempoolBlocks: processed {len(validated_blocks)} projected blocks")
                    handled = True
            else:
                logger.warning(f"Expected list for mempool-blocks, got {type(blocks_data)}")

        # Event Type 3: Block Signal (ADR-024 — Signal-Only pattern)
        # Publishes {hash, height} to block-signals topic. The REST fetch
        # is handled by the separate block_fetcher worker.
        if "block" in data:
            block_signal = data.get("block", {})
            block_hash = block_signal.get("id")
            block_height = block_signal.get("height")

            if block_hash:
                signal_payload = json.dumps(
                    {"hash": block_hash, "height": block_height}
                ).encode("utf-8")

                await producer.send(
                    key="block_signal",
                    value=signal_payload,
                    topic=settings.block_signals_topic,
                )
                logger.info(
                    f"Block signal published: height={block_height}, "
                    f"hash={block_hash[:16]}..."
                )

            handled = True

        if not handled:
            logger.warning(f"Unknown message structure: {list(data.keys())}")

    except ValidationError as e:
        logger.error(f"Pydantic validation error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in route_message: {e}", exc_info=True)


async def mempool_ingestor() -> None:
    """Main ingestion loop with async producer lifecycle and reconnection logic."""
    producer = MempoolProducer()
    await producer.start()
    retry_delay = 5  # seconds

    try:
        while True:
            try:
                async with websockets.connect(
                    settings.mempool_ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                ) as websocket:
                    logger.info(f"Connected to {settings.mempool_ws_url}")

                    # Init handshake
                    await websocket.send(json.dumps({"action": "init"}))

                    # Subscribe to all data channels
                    await websocket.send(json.dumps({
                        "action": "want",
                        "data": ["mempool-blocks", "stats", "blocks"],
                    }))

                    logger.info(
                        f"Subscribed to: mempool-blocks, stats, blocks. "
                        f"Producing to: {settings.mempool_topic}, "
                        f"{settings.block_signals_topic}"
                    )

                    # Message loop
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await route_message(data, producer)
                        except json.JSONDecodeError:
                            logger.error("JSON decode error")
                            continue

            except Exception as e:
                logger.error(f"Connection error: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(mempool_ingestor())