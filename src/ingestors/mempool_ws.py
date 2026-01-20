import asyncio
import websockets
import json
from src.common.kafka_producer import MempoolProducer

async def mempool_streamer():
    """
    Connects to the Mempool.space WebSocket API and streams data to Redpanda.
    """
    uri = "wss://mempool.space/api/v1/ws"
    topic = "mempool-raw"
    
    # Instance of our infrastructure client
    producer = MempoolProducer()
    
    print(f"Connecting to {uri}...")
    
    async with websockets.connect(uri) as ws:
        # Protocol handshake: request global stats and mempool tracking
        await ws.send(json.dumps({"action": "want-stats"}))
        await ws.send(json.dumps({"track-mempool": True}))
        
        print(f"Stream established. Producing events to topic: {topic}")
        
        try:
            async for message in ws:
                data = json.loads(message)
                
                # Determine message type for Kafka partitioning/keying
                msg_type = "stats" if "mempoolInfo" in data else "batch"
                
                # Forward data to the message broker
                producer.produce(topic=topic, key=msg_type, value=data)
                
                if msg_type == "stats":
                    m_info = data["mempoolInfo"]
                    print(f"Checkpoint | Txs: {m_info['size']} | Fees: {m_info['min_fee']} sat/vB")
                    
        except websockets.exceptions.ConnectionClosed:
            print("Server closed connection. Terminating ingestor.")
        finally:
            producer.flush()

if __name__ == "__main__":
    try:
        asyncio.run(mempool_streamer())
    except KeyboardInterrupt:
        print("\nIngestor stopped by user.")