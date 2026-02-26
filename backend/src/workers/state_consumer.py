"""State Consumer — materializes Kafka events into PostgreSQL.

Consumes from Redpanda topic (mempool-raw) under consumer group
'mempool-state-writers' and persists state to PostgreSQL tables:
  - stats         → MempoolSnapshot (INSERT, append-only timeseries)
  - confirmed_block → BlockRecord (UPSERT, idempotent by height)
  - mempool_block → debug log only (skipped for now)

Usage:
    cd backend && uv run python -m src.workers.state_consumer
"""

import asyncio
import json

from aiokafka import AIOKafkaConsumer
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.config import settings
from src.infrastructure.database.session import engine, async_session
from src.infrastructure.database.models import Base, BlockRecord, MempoolSnapshot
from src.domain.schemas import MempoolStats, ConfirmedBlock


async def _handle_stats(value: bytes) -> None:
    """Materialize a MempoolStats event into a MempoolSnapshot row."""
    stats = MempoolStats.model_validate_json(value)
    info = stats.mempool_info

    async with async_session() as session:
        snapshot = MempoolSnapshot(
            tx_count=info.size,
            total_bytes=info.bytes,
            total_fee_sats=info.total_fee,
            median_fee=info.mempool_min_fee or 0.0,
        )
        session.add(snapshot)
        await session.commit()

    logger.info(
        f"MempoolSnapshot: txs={info.size}, "
        f"bytes={info.bytes}, fee_sats={info.total_fee}"
    )


async def _handle_confirmed_block(value: bytes) -> None:
    """Materialize a ConfirmedBlock event into a BlockRecord row (idempotent)."""
    block = ConfirmedBlock.model_validate_json(value)

    stmt = pg_insert(BlockRecord).values(
        height=block.height,
        hash=block.id,
        timestamp=block.timestamp,
        tx_count=block.tx_count,
        size=block.size,
        median_fee=block.extras.median_fee,
        total_fees=block.extras.total_fees,
    ).on_conflict_do_nothing(index_elements=["height"])

    async with async_session() as session:
        await session.execute(stmt)
        await session.commit()

    logger.info(
        f"BlockRecord: height={block.height}, "
        f"median_fee={block.extras.median_fee:.2f} sat/vB, "
        f"tx_count={block.tx_count}"
    )


async def _handle_message(key: str | None, value: bytes) -> None:
    """Route a Kafka message to the appropriate handler by key."""
    if key == "stats":
        await _handle_stats(value)
    elif key == "confirmed_block":
        await _handle_confirmed_block(value)
    elif key == "mempool_block":
        logger.debug("mempool_block event received (skipped)")
    else:
        logger.warning(f"Unknown message key: {key}")


async def state_consumer() -> None:
    """Main consumer loop with DDL bootstrap and graceful shutdown."""

    # 1. Bootstrap DDL — create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DDL bootstrap complete — tables ready.")

    # 2. Start Kafka consumer
    consumer = AIOKafkaConsumer(
        settings.mempool_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="mempool-state-writers",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info(
        f"Consuming from '{settings.mempool_topic}' "
        f"(group: mempool-state-writers)"
    )

    # 3. Consume loop with graceful shutdown
    try:
        async for msg in consumer:
            key = msg.key.decode("utf-8") if msg.key else None
            try:
                await _handle_message(key, msg.value)
            except ValidationError as e:
                logger.error(f"Schema validation failed for key={key}: {e}")
            except Exception as e:
                logger.error(f"Failed to process message key={key}: {e}", exc_info=True)
    finally:
        await consumer.stop()
        await engine.dispose()
        logger.info("State consumer shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(state_consumer())
