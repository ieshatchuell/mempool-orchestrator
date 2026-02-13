import duckdb
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/market/mempool_data.duckdb")

print(f"🔍 Conectando a: {DB_PATH} ...")

try:
    conn = duckdb.connect(DB_PATH, read_only=True)
    
    # 1. VER DATOS - mempool_stream (projections)
    print("\n--- 📋 ÚLTIMOS 10 PROYECCIONES (Next Block) ---")
    conn.sql("""
        SELECT 
            ingestion_time, 
            block_index, 
            median_fee, 
            n_tx,
            total_fees
        FROM mempool_stream 
        WHERE block_index = 0 
        ORDER BY ingestion_time DESC 
        LIMIT 10
    """).show()

    # 2. ESTADÍSTICAS - block_history (confirmed)
    print("\n--- 📊 ESTADÍSTICAS DE MEDIAN FEE (Bloques Confirmados) ---")
    conn.sql("""
        SELECT 
            MIN(median_fee) as min_med, 
            MAX(median_fee) as max_med, 
            AVG(median_fee) as avg_med,
            COUNT(*) as total_rows
        FROM block_history
    """).show()

except Exception as e:
    print(f"❌ Error: {e}")