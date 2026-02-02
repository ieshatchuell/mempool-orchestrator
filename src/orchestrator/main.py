"""
AI Orchestrator Service – Phase 2: The Agentic Brain

Performs continuous health checks against:
1. Ollama LLM server
2. DuckDB storage (read-only)
"""
import asyncio
import os

import duckdb
import ollama
from loguru import logger

# Configuration from environment
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "mempool_data.duckdb")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
HEALTH_CHECK_INTERVAL = 30  # seconds


async def check_ollama() -> bool:
    """Verify Ollama connectivity by listing available models."""
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        models = client.list()
        model_names = [m.model for m in models.models] if models.models else []
        logger.success(f"✅ Ollama connected | Models: {model_names or 'none'}")
        return True
    except Exception as e:
        logger.error(f"❌ Ollama connection failed: {e}")
        return False


async def check_duckdb() -> bool:
    """Verify DuckDB connectivity and count rows in projected_blocks."""
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        result = conn.execute("SELECT COUNT(*) FROM projected_blocks").fetchone()
        row_count = result[0] if result else 0
        conn.close()
        logger.success(f"✅ DuckDB connected | projected_blocks rows: {row_count:,}")
        return True
    except Exception as e:
        logger.error(f"❌ DuckDB connection failed: {e}")
        return False


async def health_check_loop() -> None:
    """Main health check loop."""
    logger.info("🧠 AI Orchestrator starting...")
    logger.info(f"   DUCKDB_PATH: {DUCKDB_PATH}")
    logger.info(f"   OLLAMA_HOST: {OLLAMA_HOST}")

    while True:
        logger.info("─" * 40)
        await check_ollama()
        await check_duckdb()
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)


def main() -> None:
    """Entry point."""
    asyncio.run(health_check_loop())


if __name__ == "__main__":
    main()
