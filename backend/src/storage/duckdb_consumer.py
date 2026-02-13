import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List
import duckdb
from confluent_kafka import Consumer, KafkaError
from pydantic import ValidationError

from src.config import settings
from src.schemas import MempoolStats, MempoolBlock, ConfirmedBlock


class DuckDBConsumer:
    """
    Consumes typed mempool events from Kafka and persists them into structured DuckDB tables.
    
    Handles three event types:
    - 'stats': Mempool statistics → mempool_stats table
    - 'mempool_block': Projected blocks → mempool_stream table
    - 'confirmed_block': Mined blocks → block_history table
    """

    def __init__(self):
        """Initializes the Kafka consumer and DuckDB connection."""
        self.conf = {
            'bootstrap.servers': settings.kafka_bootstrap_servers,
            'group.id': 'mempool-storage-group',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False  # Manual commit for data integrity
        }
        self.consumer = Consumer(self.conf)

        # Ensure data directory exists (handles ../ relative paths)
        db_path = Path(settings.duckdb_path).resolve()
        os.makedirs(db_path.parent, exist_ok=True)

        self.db_conn = duckdb.connect(str(db_path))
        self._init_db()
        self.buffer = []

    def _init_db(self):
        """Creates structured tables for mempool data."""
        # Mempool Statistics Table
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS mempool_stats (
                ingestion_time TIMESTAMP NOT NULL,
                size UINTEGER NOT NULL,
                bytes UINTEGER NOT NULL,
                total_fee UBIGINT NOT NULL,
                min_fee DOUBLE NOT NULL
            )
        """)
        
        # Mempool Stream Table (speculative projections from WebSocket mempool-blocks)
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS mempool_stream (
                ingestion_time TIMESTAMP NOT NULL,
                block_index UTINYINT NOT NULL,
                block_size UINTEGER NOT NULL,
                block_v_size DOUBLE NOT NULL,
                n_tx UINTEGER NOT NULL,
                total_fees UBIGINT NOT NULL,
                median_fee DOUBLE NOT NULL,
                fee_range JSON NOT NULL
            )
        """)

        # Block History Table (confirmed blocks from backfill + live WebSocket signals)
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS block_history (
                ingestion_time TIMESTAMP NOT NULL,
                height UINTEGER NOT NULL,
                block_hash VARCHAR NOT NULL,
                block_size UINTEGER NOT NULL,
                block_v_size DOUBLE NOT NULL,
                n_tx UINTEGER NOT NULL,
                total_fees UBIGINT NOT NULL,
                median_fee DOUBLE NOT NULL,
                fee_range JSON NOT NULL,
                pool_name VARCHAR
            )
        """)
        
        print("📦 DuckDB initialized. Tables: mempool_stats, mempool_stream, block_history.")

    def consume_loop(self):
        """Main loop to consume messages and trigger batch writes."""
        self.consumer.subscribe([settings.mempool_topic])
        print(f"📥 Consuming from {settings.mempool_topic} (Batch size: {settings.duckdb_batch_size})...")

        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"❌ Kafka Error: {msg.error()}")
                        break

                # Process message with resilient parsing
                self.process_message(msg)

                # Flush buffer when batch size is reached
                if len(self.buffer) >= settings.duckdb_batch_size:
                    self._flush_to_db()

        except KeyboardInterrupt:
            print("\n🛑 Shutdown signal received.")
        finally:
            self._cleanup()

    def process_message(self, msg):
        """
        Routes Kafka messages to appropriate handlers based on key.
        
        - b'stats'           → Parse as MempoolStats     → mempool_stats
        - b'mempool_block'   → Parse as List[MempoolBlock] → mempool_stream
        - b'confirmed_block' → Parse as ConfirmedBlock    → block_history
        """
        try:
            key = msg.key()
            value_str = msg.value().decode('utf-8')
            ingestion_time = datetime.now(timezone.utc)

            if key == b'stats':
                # Parse and validate as MempoolStats
                data = json.loads(value_str)
                stats = MempoolStats.model_validate(data)
                
                info = stats.mempool_info
                record = (
                    ingestion_time,
                    info.size,
                    info.bytes,
                    info.total_fee,
                    info.mempool_min_fee or 0.0
                )
                self.buffer.append(('stats', record))

            elif key == b'mempool_block':
                # Parse and validate as List[MempoolBlock]
                data = json.loads(value_str)
                
                # Handle both wrapped and unwrapped list formats
                if isinstance(data, dict) and "mempool-blocks" in data:
                    blocks_data = data["mempool-blocks"]
                elif isinstance(data, list):
                    blocks_data = data
                else:
                    raise ValueError(f"Unexpected mempool_block format: {type(data)}")
                
                blocks: List[MempoolBlock] = [MempoolBlock.model_validate(block) for block in blocks_data]
                
                for block_index, block in enumerate(blocks):
                    record = (
                        ingestion_time,
                        block_index,
                        block.block_size,
                        block.block_v_size,
                        block.n_tx,
                        block.total_fees,
                        block.median_fee,
                        json.dumps(block.fee_range)
                    )
                    self.buffer.append(('mempool_block', record))

            elif key == b'confirmed_block':
                # Parse and validate as ConfirmedBlock
                data = json.loads(value_str)
                block = ConfirmedBlock.model_validate(data)
                
                pool_name = None
                if block.extras.pool:
                    pool_name = block.extras.pool.get("name")

                record = (
                    ingestion_time,
                    block.height,
                    block.id,
                    block.size,
                    block.extras.virtual_size,
                    block.tx_count,
                    block.extras.total_fees,
                    block.extras.median_fee,
                    json.dumps(block.extras.fee_range),
                    pool_name,
                )
                self.buffer.append(('confirmed_block', record))

            else:
                print(f"⚠️ Unknown message key: {key!r}")

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decode error: {e}")
        except ValidationError as e:
            print(f"⚠️ Validation error for key {msg.key()!r}: {e}")
        except Exception as e:
            print(f"⚠️ Unexpected error processing message: {e}")

    def _cleanup(self):
        """Final flush and resource release."""
        print("🧹 Cleaning up resources...")
        if self.buffer:
            print(f"Final flush: {len(self.buffer)} records.")
            self._flush_to_db()
        
        if hasattr(self, 'db_conn'):
            self.db_conn.close()
            print("🔒 DuckDB connection closed.")
        
        if hasattr(self, 'consumer'):
            self.consumer.close()
            print("🔌 Kafka consumer closed.")

    def _flush_to_db(self):
        """Persists the buffer to DuckDB and commits Kafka offsets."""
        if not self.buffer:
            return

        try:
            # Separate records by type
            stats_records = [r for k, r in self.buffer if k == 'stats']
            stream_records = [r for k, r in self.buffer if k == 'mempool_block']
            history_records = [r for k, r in self.buffer if k == 'confirmed_block']

            # Batch insert stats
            if stats_records:
                self.db_conn.executemany(
                    """INSERT INTO mempool_stats 
                       (ingestion_time, size, bytes, total_fee, min_fee) 
                       VALUES (?, ?, ?, ?, ?)""",
                    stats_records
                )
                print(f"✅ Inserted {len(stats_records)} stats records.")

            # Batch insert mempool stream (projected blocks)
            if stream_records:
                self.db_conn.executemany(
                    """INSERT INTO mempool_stream 
                       (ingestion_time, block_index, block_size, block_v_size, n_tx, total_fees, median_fee, fee_range) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    stream_records
                )
                print(f"✅ Inserted {len(stream_records)} mempool stream records.")

            # Batch insert block history (confirmed blocks)
            if history_records:
                self.db_conn.executemany(
                    """INSERT INTO block_history 
                       (ingestion_time, height, block_hash, block_size, block_v_size, n_tx, total_fees, median_fee, fee_range, pool_name) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    history_records
                )
                print(f"✅ Inserted {len(history_records)} block history records.")

            # Only commit Kafka offset after successful DB writes
            self.consumer.commit()
            self.buffer = []

        except Exception as e:
            print(f"❌ CRITICAL: Failed to persist batch to DuckDB: {e}")


if __name__ == "__main__":
    DuckDBConsumer().consume_loop()