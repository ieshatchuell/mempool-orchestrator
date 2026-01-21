import asyncio
import websockets
import json
from src.config import settings
from src.common.kafka_producer import MempoolProducer

def classify_message(data: dict) -> str:
    """
    Determines the Kafka key based on the message structure using Pattern Matching.
    
    Args:
        data (dict): The decoded JSON payload from the WebSocket.
        
    Returns:
        str: The routing key ('stats', 'block', 'init_data', or 'batch').
    """
    match data:
        case {"mempoolInfo": _}:
            return "stats"
        case {"block": _}:
            return "block"
        case {"conversions": _}:
            return "init_data"
        case _:
            # Default to batch for transaction lists or unknown structures
            return "batch"

async def mempool_ingestor():
    """
    Main ingestion loop to stream data from Mempool WebSocket to Kafka.
    """
    producer = MempoolProducer()
    
    async with websockets.connect(settings.mempool_ws_url, ping_interval=20) as websocket:
        print(f"🟢 Connected to {settings.mempool_ws_url}")
        
        # --- ROBUST PROTOCOL (Standard v1 Handshake) ---
        await websocket.send(json.dumps({"action": "init"}))
        await websocket.send(json.dumps({"action": "want", "data": ["stats", "mempool-blocks"]}))
        
        print(f"🚀 Stream subscriptions sent. Producing to topic: {settings.mempool_topic}")

        async for message in websocket:
            data = json.loads(message)
            key = classify_message(data)
            
            producer.produce(
                topic=settings.mempool_topic,
                key=key,
                value=json.dumps(data).encode('utf-8')
            )

if __name__ == "__main__":
    try:
        asyncio.run(mempool_ingestor())
    except KeyboardInterrupt:
        print("\n🔴 Ingestor stopped by user.")