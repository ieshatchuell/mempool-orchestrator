"""Backfill the last 144 blocks (~24h) from mempool.space REST API into PostgreSQL.

Maintenance script — flushes the blocks table and repopulates from scratch
to guarantee a contiguous timeline with no gaps.

Usage:
    cd backend && uv run python -m scripts.backfill_blocks
"""

import asyncio

import httpx
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.config import settings
from src.domain.schemas import ConfirmedBlock
from src.infrastructure.database.session import engine, async_session
from src.infrastructure.database.models import Base, BlockRecord

TARGET_BLOCKS = 144
BLOCKS_PER_PAGE = 15


async def backfill() -> None:
    """Flush blocks table, fetch 144 blocks from REST API, and bulk insert."""

    # 1. DDL bootstrap
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DDL bootstrap complete.")

    # 2. Flush blocks table
    async with async_session() as session:
        result = await session.execute(delete(BlockRecord))
        await session.commit()
        logger.info(f"Flushed {result.rowcount} existing blocks.")

    # 3. Paginated fetch from mempool.space REST API
    all_blocks: list[ConfirmedBlock] = []
    url = f"{settings.mempool_api_url}/v1/blocks"

    async with httpx.AsyncClient(timeout=30) as client:
        page = 1
        while len(all_blocks) < TARGET_BLOCKS:
            resp = await client.get(url)
            resp.raise_for_status()
            batch = resp.json()

            if not batch:
                logger.warning("Empty response from API — stopping pagination.")
                break

            validated = 0
            for raw in batch:
                try:
                    block = ConfirmedBlock.model_validate(raw)
                    all_blocks.append(block)
                    validated += 1
                except ValidationError as e:
                    logger.error(f"Validation failed for block: {e}")
                    continue

            logger.info(
                f"Page {page}: fetched {len(batch)}, validated {validated}, "
                f"total {len(all_blocks)}/{TARGET_BLOCKS}"
            )

            # Paginate: next call uses last block's height
            last_height = batch[-1].get("height")
            if last_height is None:
                break
            url = f"{settings.mempool_api_url}/v1/blocks/{last_height}"
            page += 1

    # Truncate to exactly TARGET_BLOCKS
    all_blocks = all_blocks[:TARGET_BLOCKS]

    # 4. Bulk insert with ON CONFLICT DO NOTHING
    if all_blocks:
        values = [
            {
                "height": b.height,
                "hash": b.id,
                "timestamp": b.timestamp,
                "tx_count": b.tx_count,
                "size": b.size,
                "median_fee": b.extras.median_fee,
                "total_fees": b.extras.total_fees,
            }
            for b in all_blocks
        ]

        stmt = pg_insert(BlockRecord).values(values).on_conflict_do_nothing(
            index_elements=["height"]
        )

        async with async_session() as session:
            await session.execute(stmt)
            await session.commit()

    # 5. Dispose engine
    await engine.dispose()

    height_range = f"{all_blocks[-1].height}..{all_blocks[0].height}" if all_blocks else "N/A"
    logger.info(
        f"Backfill complete: {len(all_blocks)} blocks inserted "
        f"(heights {height_range})"
    )


if __name__ == "__main__":
    asyncio.run(backfill())
