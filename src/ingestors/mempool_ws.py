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
    # Silence conversions noise (initialization data)
    if "conversions" in data:
        return
    
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
            return
        
        # Event Type 2: Mempool Blocks (projected blocks)
        if "mempool-blocks" in data or isinstance(data.get("blocks"), list):
            # Handle both {"mempool-blocks": [...]} and {"blocks": [...]} formats
            blocks_data = data.get("mempool-blocks") or data.get("blocks", [])
            
            if not isinstance(blocks_data, list):
                logger.warning(f"Expected list for mempool-blocks, got {type(blocks_data)}")
                return
            
            # Validate each block
            validated_blocks: List[Dict[str, Any]] = []
            for block_data in blocks_data:
                try:
                    block = MempoolBlock.model_validate(block_data)
                    validated_blocks.append(block.model_dump())
                except ValidationError as e:
                    logger.error(f"❌ MempoolBlock validation failed: {e}")
                    continue
            
            if validated_blocks:
                producer.produce(
                    topic=settings.mempool_topic,
                    key="mempool_block",
                    value=json.dumps(validated_blocks).encode("utf-8")
                )
                logger.info(f"✅ MempoolBlocks: validated {len(validated_blocks)} projected blocks")
            return
        
        # Event Type 3: Confirmed Block (signal only - future feature)
        if "block" in data:
            block_hash = data.get("block", {}).get("id", "unknown")
            block_height = data.get("block", {}).get("height", "unknown")
            logger.info(f"📦 Confirmed block signal: height={block_height}, hash={block_hash[:16]}... (not processed)")
            return
        
        # Unknown event type
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
                await websocket.send(json.dumps({
                    "action": "want",
                    "data": ["stats", "mempool-blocks"]
                }))
                
                logger.info(f"🚀 Subscribed to stats and mempool-blocks. Producing to: {settings.mempool_topic}")
                
                # Message loop
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        route_message(data, producer)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON decode error: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error processing message: {e}", exc_info=True)
                        continue
        
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"🔴 WebSocket error: {e}. Reconnecting in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
        except KeyboardInterrupt:
            logger.info("🔴 Ingestor stopped by user")
            raise
        except Exception as e:
            logger.error(f"🔴 Unexpected error: {e}. Reconnecting in {retry_delay}s...", exc_info=True)
            await asyncio.sleep(retry_delay)


if __name__ == "__main__":
    try:
        asyncio.run(mempool_ingestor())
    except KeyboardInterrupt:
        logger.info("👋 Shutdown complete")