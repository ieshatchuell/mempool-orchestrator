import duckdb
import os

DB_PATH = "mempool_data.duckdb"

print(f"🔍 Conectando a: {DB_PATH} ...")

try:
    conn = duckdb.connect(DB_PATH, read_only=True)
    
    # 1. VER DATOS (Corregido: quitamos min_fee)
    print("\n--- 📋 ÚLTIMOS 10 REGISTROS (Next Block) ---")
    conn.sql("""
        SELECT 
            ingestion_time, 
            block_index, 
            median_fee, 
            n_tx,
            total_fees
        FROM projected_blocks 
        WHERE block_index = 0 
        ORDER BY ingestion_time DESC 
        LIMIT 10
    """).show()

    # 2. ESTADÍSTICAS (Corregido)
    print("\n--- 📊 ESTADÍSTICAS DE MEDIAN FEE ---")
    conn.sql("""
        SELECT 
            MIN(median_fee) as min_med, 
            MAX(median_fee) as max_med, 
            AVG(median_fee) as avg_med,
            COUNT(*) as total_rows
        FROM projected_blocks
        WHERE block_index = 0
    """).show()

except Exception as e:
    print(f"❌ Error: {e}")