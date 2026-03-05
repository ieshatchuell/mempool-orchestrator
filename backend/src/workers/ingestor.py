"""Radar ingestion worker — real-time mempool stats, projected blocks, and confirmed blocks.

Connects to Mempool.space WebSocket API and streams validated events to Kafka (Redpanda)
via the async MempoolProducer.

Confirmed blocks use the Signal & Fetch pattern:
1. WebSocket sends a block signal (hash, height)
2. We fetch full block data via REST API (GET /api/v1/block/{hash})
3. Validated ConfirmedBlock is produced to Kafka
"""

import asyncio
import json
from typing import Any

import httpx
import websockets
from loguru import logger
from pydantic import ValidationError

from src.core.config import settings
from src.infrastructure.messaging.producer import MempoolProducer
from src.domain.schemas import MempoolStats, MempoolBlock, ConfirmedBlock

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

    Signal & Fetch pattern: the WebSocket block event is a signal.
    We fetch the complete data (with extras/fees) from the REST API.

    Args:
        block_hash: The block hash from the WebSocket signal.

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

        # Event Type 3: Confirmed Block (Signal & Fetch pattern)
        if "block" in data:
            block_signal = data.get("block", {})
            block_hash = block_signal.get("id")
            block_height = block_signal.get("height")

            if block_hash:
                logger.info(f"Block signal received: height={block_height}, hash={block_hash[:16]}...")

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
                        f"Producing to: {settings.mempool_topic}"
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
        if _http_client and not _http_client.is_closed:
            await _http_client.aclose()


if __name__ == "__main__":
    asyncio.run(mempool_ingestor())