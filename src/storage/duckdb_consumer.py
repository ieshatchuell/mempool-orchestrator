import json
from datetime import datetime, timezone
from typing import List
import duckdb
from confluent_kafka import Consumer, KafkaError
from pydantic import ValidationError

from src.config import settings
from src.schemas import MempoolStats, MempoolBlock


class DuckDBConsumer:
    """
    Consumes typed mempool events from Kafka and persists them into structured DuckDB tables.
    
    Handles two event types:
    - 'stats': Mempool statistics → mempool_stats table
    - 'mempool_block': Projected blocks → projected_blocks table
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
        self.db_conn = duckdb.connect(settings.duckdb_path)
        self._init_db()
        self.buffer = []

    def _init_db(self):
        """Creates structured tables for mempool stats and projected blocks."""
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
        
        # Projected Blocks Table
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS projected_blocks (
                ingestion_time TIMESTAMP NOT NULL,
                block_size UINTEGER NOT NULL,
                block_v_size UINTEGER NOT NULL,
                n_tx UINTEGER NOT NULL,
                total_fees UBIGINT NOT NULL,
                median_fee DOUBLE NOT NULL
            )
        """)
        
        print("📦 DuckDB initialized. Tables 'mempool_stats' and 'projected_blocks' ready.")

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
        
        - b'stats' → Parse as MempoolStats → Insert into mempool_stats
        - b'mempool_block' → Parse as List[MempoolBlock] → Insert into projected_blocks
        """
        try:
            key = msg.key()
            value_str = msg.value().decode('utf-8')
            ingestion_time = datetime.now(timezone.utc)

            if key == b'stats':
                # Parse and validate as MempoolStats
                data = json.loads(value_str)
                stats = MempoolStats.model_validate(data)
                
                # Extract fields from nested structure
                info = stats.mempool_info
                record = (
                    ingestion_time,
                    info.size,
                    info.bytes,
                    int(info.total_fee * 100_000_000),  # Convert BTC to Satoshis
                    info.mempool_min_fee or 0.0
                )
                self.buffer.append(('stats', record))

            elif key == b'mempool_block':
                # Parse and validate as List[MempoolBlock]
                data = json.loads(value_str)
                blocks: List[MempoolBlock] = [MempoolBlock.model_validate(block) for block in data]
                
                # Insert each block with the same ingestion timestamp
                for block in blocks:
                    record = (
                        ingestion_time,
                        block.block_size,
                        block.block_v_size,
                        block.n_tx,
                        block.total_fees,
                        block.median_fee
                    )
                    self.buffer.append(('mempool_block', record))

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
            block_records = [r for k, r in self.buffer if k == 'mempool_block']

            # Batch insert stats
            if stats_records:
                self.db_conn.executemany(
                    """INSERT INTO mempool_stats 
                       (ingestion_time, size, bytes, total_fee, min_fee) 
                       VALUES (?, ?, ?, ?, ?)""",
                    stats_records
                )
                print(f"✅ Inserted {len(stats_records)} stats records.")

            # Batch insert projected blocks
            if block_records:
                self.db_conn.executemany(
                    """INSERT INTO projected_blocks 
                       (ingestion_time, block_size, block_v_size, n_tx, total_fees, median_fee) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    block_records
                )
                print(f"✅ Inserted {len(block_records)} projected block records.")

            # Only commit Kafka offset after successful DB writes
            self.consumer.commit()
            self.buffer = []

        except Exception as e:
            print(f"❌ CRITICAL: Failed to persist batch to DuckDB: {e}")


if __name__ == "__main__":
    DuckDBConsumer().consume_loop()