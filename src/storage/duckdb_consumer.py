import json
import duckdb
from confluent_kafka import Consumer, KafkaError
from src.config import settings

class DuckDBConsumer:
    """
    Consumes raw mempool events from Kafka and persists them into DuckDB.
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
        """Ensures the target table and parsed views exist."""
        # Bronze Layer: Raw Data
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_mempool (
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                key VARCHAR,
                data JSON
            )
        """)
        
        # Silver Layer: Parsed Stats View
        # Extract metrics from 'mempoolInfo' object comming from 'stats' messages
        self.db_conn.execute("""
            CREATE OR REPLACE VIEW v_mempool_stats AS
            SELECT 
                timestamp,
                (data->>'$.mempoolInfo.size')::INTEGER as tx_count,
                (data->>'$.mempoolInfo.bytes')::BIGINT as total_bytes,
                (data->>'$.mempoolInfo.usage')::BIGINT as memory_usage,
                -- El campo total_fee ya viene en BTC en el JSON de stats
                (data->>'$.mempoolInfo.total_fee')::DOUBLE as total_fee_btc,
                -- Cálculo derivado: Fee media por transacción en Satoshis
                ((data->>'$.mempoolInfo.total_fee')::DOUBLE * 100000000.0) / 
                 NULLIF((data->>'$.mempoolInfo.size')::INTEGER, 0) as avg_tx_fee_sats
            FROM raw_mempool
            WHERE key = 'stats'
        """)
        print(f"📦 DuckDB initialized. Bronze table and Silver view 'v_mempool_stats' ready.")

    def consume_loop(self):
        """Main loop to consume messages and trigger batch writes."""
        self.consumer.subscribe([settings.mempool_topic])
        print(f"📥 Consuming from {settings.mempool_topic} (Batch size: {settings.duckdb_batch_size})...")

        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None: continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF: continue
                    else: print(f"Error: {msg.error()}"); break

                key = msg.key().decode('utf-8') if msg.key() else "unknown"
                value = msg.value().decode('utf-8')
                self.buffer.append((key, value))

                if len(self.buffer) >= settings.duckdb_batch_size:
                    self._flush_to_db()

        except KeyboardInterrupt:
            print("\n🛑 Shutdown signal received.")
        finally:
            self._cleanup()

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
            # Efficient batch insertion
            self.db_conn.executemany(
                "INSERT INTO raw_mempool (key, data) VALUES (?, ?)", 
                self.buffer
            )
            self.consumer.commit()  # Only commit Kafka after DB write is successful
            print(f"✅ Persisted {len(self.buffer)} records to DuckDB.")
            self.buffer = []
        except Exception as e:
            print(f"CRITICAL: Failed to persist batch to DuckDB: {e}")

if __name__ == "__main__":
    DuckDBConsumer().consume_loop()