"""Radar ingestion pattern for real-time mempool stats and projected blocks.

Connects to Mempool.space WebSocket API and streams validated events to Kafka.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

import websockets
from pydantic import ValidationError

from src.config import settings
from src.common.kafka_producer import MempoolProducer
from src.schemas import MempoolStats, MempoolBlock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def route_message(data: Dict[str, Any], producer: MempoolProducer) -> None:
    """Route incoming WebSocket message to appropriate handler with Pydantic validation.
    
    Args:
        data: Decoded JSON payload from WebSocket
        producer: Kafka producer instance
    """
    # 1. Silence Noise (Initialization & UI data)
    ignored_keys = {"conversions", "loadingIndicators", "init"}
    if any(key in data for key in ignored_keys):
        return
    
    # Track if we handled the message to warn about unknown structures
    handled = False

    try:
        # Event Type 1: Mempool Stats
        if "mempoolInfo" in data:
            stats = MempoolStats.model_validate(data)
            producer.produce(
                topic=settings.mempool_topic,
                key="stats",
                value=stats.model_dump_json().encode("utf-8")
            )
            logger.info(f"✅ MempoolStats: size={stats.mempool_info.size}, bytes={stats.mempool_info.bytes}")
            handled = True
            # NO RETURN HERE: Continue checking for other keys in the same message
        
        # Event Type 2: Mempool Blocks (projected blocks)
        # Check specifically for the key we saw in the sniff script
        if "mempool-blocks" in data or "blocks" in data:

            # Handle both formats
            blocks_data = data.get("mempool-blocks") or data.get("blocks", [])
            
            if isinstance(blocks_data, list):
                # Validate each block
                validated_blocks: List[Dict[str, Any]] = []
                for block_data in blocks_data:
                    try:
                        block = MempoolBlock.model_validate(block_data)
                        validated_blocks.append(block.model_dump())
                    except ValidationError as e:
                        logger.error(f"❌ MempoolBlock validation failed: {e} | Data: {block_data}")
                        continue
                
                if validated_blocks:
                    producer.produce(
                        topic=settings.mempool_topic,
                        key="mempool_block",
                        value=json.dumps(validated_blocks).encode("utf-8")
                    )
                    logger.info(f"✅ MempoolBlocks: processed {len(validated_blocks)} blocks")
                    handled = True
            else:
                logger.warning(f"⚠️ Expected list for blocks, got {type(blocks_data)}")

        # Event Type 3: Confirmed Block (signal)
        if "block" in data:
            block_info = data.get("block", {})
            logger.info(f"📦 Confirmed block signal: height={block_info.get('height')}")
            handled = True
        
        # Unknown event type
        if not handled:
            logger.warning(f"⚠️  Unknown message structure: {list(data.keys())}")
    
    except ValidationError as e:
        logger.error(f"❌ Pydantic validation error: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error in route_message: {e}", exc_info=True)


async def mempool_ingestor() -> None:
    """Main ingestion loop with reconnection logic."""
    producer = MempoolProducer()
    retry_delay = 5  # seconds
    
    while True:
        try:
            async with websockets.connect(
                settings.mempool_ws_url,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                logger.info(f"🟢 Connected to {settings.mempool_ws_url}")
                
                # Init handshake
                await websocket.send(json.dumps({"action": "init"}))
                
                # Subscribe explicitly
                await websocket.send(json.dumps({
                    "action": "want",
                    "data": ["mempool-blocks", "stats"]
                }))
                
                logger.info(f"🚀 Subscribed. Producing to: {settings.mempool_topic}")
                
                # Message loop
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        route_message(data, producer)
                    except json.JSONDecodeError:
                        logger.error("❌ JSON decode error")
                        continue
        
        except Exception as e:
            logger.error(f"🔴 Connection error: {e}. Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)


if __name__ == "__main__":
    asyncio.run(mempool_ingestor())