import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import duckdb
import redis
from confluent_kafka import Consumer, KafkaError
from pydantic import ValidationError

from src.config import settings
from src.schemas import MempoolStats, MempoolBlock, ConfirmedBlock
from src.api.queries import (
    query_mempool_stats,
    query_recent_blocks,
    query_orchestrator_status,
    query_watchlist_advisories,
)


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

        # Redis client for CQRS projection (dashboard read layer)
        self._redis = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

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
                height UINTEGER NOT NULL UNIQUE,
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
        
        if hasattr(self, '_redis'):
            self._redis.close()
            print("🔴 Redis connection closed.")
        
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

            # UPSERT block history (confirmed blocks) — dedup by height
            if history_records:
                for record in history_records:
                    self.db_conn.execute(
                        """INSERT INTO block_history 
                           (ingestion_time, height, block_hash, block_size, block_v_size, n_tx, total_fees, median_fee, fee_range, pool_name) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(height) DO UPDATE SET
                               ingestion_time = EXCLUDED.ingestion_time,
                               block_hash = EXCLUDED.block_hash,
                               block_size = EXCLUDED.block_size,
                               block_v_size = EXCLUDED.block_v_size,
                               n_tx = EXCLUDED.n_tx,
                               total_fees = EXCLUDED.total_fees,
                               median_fee = EXCLUDED.median_fee,
                               fee_range = EXCLUDED.fee_range,
                               pool_name = EXCLUDED.pool_name""",
                        list(record),
                    )
                print(f"✅ Upserted {len(history_records)} block history records.")

                # Retention policy: keep only the latest 144 blocks
                self.db_conn.execute("""
                    DELETE FROM block_history
                    WHERE height NOT IN (
                        SELECT height FROM block_history ORDER BY height DESC LIMIT 144
                    )
                """)

            # Only commit Kafka offset after successful DB writes
            self.consumer.commit()
            self._project_to_redis()
            self.buffer = []

        except Exception as e:
            print(f"❌ CRITICAL: Failed to persist batch to DuckDB: {e}")

    def _project_to_redis(self):
        """Project dashboard views from DuckDB to Redis after each flush.

        Uses the same self.db_conn (R/W) — MVCC guarantees consistent reads
        of committed data within the same process. Non-critical: if Redis is
        unreachable, DuckDB writes are unaffected.
        """
        try:
            # Market data projections (same connection that just wrote)
            self._redis.set(
                "dashboard:mempool_stats",
                json.dumps(query_mempool_stats(self.db_conn)),
            )
            self._redis.set(
                "dashboard:recent_blocks",
                json.dumps(query_recent_blocks(self.db_conn, limit=10)),
            )

            status = query_orchestrator_status(self.db_conn)
            self._redis.set(
                "dashboard:orchestrator_status",
                json.dumps(status),
            )

            # Watchlist projection (separate DB — read_only, opened briefly)
            try:
                history_path = str(Path(settings.agent_history_path).resolve())
                history_conn = duckdb.connect(history_path, read_only=True)
                try:
                    target_fee = status.get("current_median_fee", 1.0)
                    watchlist_data = query_watchlist_advisories(
                        history_conn, target_fee,
                    )
                    self._redis.set(
                        "dashboard:watchlist",
                        json.dumps(watchlist_data),
                    )
                finally:
                    history_conn.close()
            except Exception:
                # Watchlist DB may not exist yet — not critical
                pass

            print("📡 Dashboard projected to Redis.")

        except redis.ConnectionError:
            print("⚠️ Redis unreachable — skipping projection (DuckDB writes OK)")
        except Exception as e:
            print(f"⚠️ Projection error: {e}")


if __name__ == "__main__":
    DuckDBConsumer().consume_loop()