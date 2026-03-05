"""Incremental block backfill worker.

Detects gaps between the highest block in PostgreSQL and the chain tip,
then fetches only the missing blocks from the mempool.space REST API.

Can be invoked:
- Programmatically via `incremental_backfill()` (API lifespan, scripts)
- Directly via `python -m src.workers.backfill`

Design principles:
- Non-destructive: INSERT ... ON CONFLICT DO NOTHING (safe for replays)
- Incremental: only fetches blocks newer than max(height) in DB
- Graceful degradation: failures are logged, never crash the caller
"""

import asyncio

import httpx
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.config import settings
from src.domain.schemas import ConfirmedBlock
from src.infrastructure.database.session import engine, async_session
from src.infrastructure.database.models import Base, BlockRecord

# Default: ~24h of blocks
DEFAULT_TARGET_BLOCKS = 144
BLOCKS_PER_PAGE = 15


async def _get_chain_tip(client: httpx.AsyncClient) -> int | None:
    """Fetch the current chain tip height from mempool.space.

    Uses GET /api/blocks/tip/height which returns a plain integer.
    """
    url = f"{settings.mempool_api_url}/blocks/tip/height"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return int(resp.text.strip())
    except Exception as e:
        logger.error(f"Failed to fetch chain tip: {e}")
        return None


async def _get_db_max_height() -> int | None:
    """Query the highest block height currently stored in PostgreSQL."""
    async with async_session() as session:
        result = await session.execute(
            select(func.max(BlockRecord.height))
        )
        return result.scalar()


async def _fetch_blocks_in_range(
    client: httpx.AsyncClient,
    start_height: int,
    count: int,
) -> list[ConfirmedBlock]:
    """Fetch blocks from mempool.space REST API, paginated.

    The API returns blocks in descending order starting from `start_height`.
    GET /api/v1/blocks/{start_height} returns up to 15 blocks.

    Args:
        client: Async HTTP client.
        start_height: The height to start fetching from (descending).
        count: Maximum number of blocks to fetch.

    Returns:
        List of validated ConfirmedBlock objects.
    """
    all_blocks: list[ConfirmedBlock] = []
    url = f"{settings.mempool_api_url}/v1/blocks/{start_height}"

    page = 1
    while len(all_blocks) < count:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            logger.error(f"REST API fetch failed (page {page}): {e}")
            break

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

        logger.debug(
            f"Page {page}: fetched {len(batch)}, validated {validated}, "
            f"total {len(all_blocks)}/{count}"
        )

        # Paginate: next call uses last block's height
        last_height = batch[-1].get("height")
        if last_height is None:
            break
        url = f"{settings.mempool_api_url}/v1/blocks/{last_height}"
        page += 1

    return all_blocks[:count]


async def _bulk_insert_blocks(blocks: list[ConfirmedBlock]) -> int:
    """Bulk insert blocks into PostgreSQL with ON CONFLICT DO NOTHING.

    Returns:
        Number of rows actually inserted (excludes conflicts).
    """
    if not blocks:
        return 0

    values = [
        {
            "height": b.height,
            "hash": b.id,
            "timestamp": b.timestamp,
            "tx_count": b.tx_count,
            "size": b.size,
            "median_fee": b.extras.median_fee,
            "total_fees": b.extras.total_fees,
            "pool_name": b.extras.pool.get("name") if b.extras.pool else None,
            "fee_range": b.extras.fee_range if b.extras.fee_range else None,
        }
        for b in blocks
    ]

    stmt = (
        pg_insert(BlockRecord)
        .values(values)
        .on_conflict_do_nothing(index_elements=["height"])
    )

    async with async_session() as session:
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount


async def incremental_backfill(target_blocks: int = DEFAULT_TARGET_BLOCKS) -> int:
    """Fill gaps between the latest block in DB and the chain tip.

    Strategy:
    1. Query max(height) from blocks table
    2. Fetch current chain tip height from mempool.space
    3. If gap > 0: fetch only the missing blocks
    4. If DB is empty: fetch `target_blocks` from chain tip
    5. Bulk INSERT ... ON CONFLICT DO NOTHING

    Args:
        target_blocks: Max blocks to backfill when DB is empty (default: 144).

    Returns:
        Number of blocks inserted.
    """
    # DDL bootstrap
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Get chain tip
        chain_tip = await _get_chain_tip(client)
        if chain_tip is None:
            logger.warning("Cannot determine chain tip — skipping backfill.")
            return 0

        # 2. Get DB max height
        db_max = await _get_db_max_height()

        if db_max is None:
            # Empty DB: full backfill from chain tip
            gap = target_blocks
            logger.info(
                f"Empty blocks table — fetching {target_blocks} blocks "
                f"from tip {chain_tip}."
            )
        else:
            gap = chain_tip - db_max
            if gap <= 0:
                logger.info(
                    f"No gap detected: DB height {db_max} >= chain tip {chain_tip}."
                )
                return 0
            logger.info(
                f"Gap detected: DB height {db_max}, chain tip {chain_tip} "
                f"({gap} blocks missing)."
            )

        # Cap to avoid massive fetches
        fetch_count = min(gap, target_blocks)

        # 3. Fetch missing blocks
        blocks = await _fetch_blocks_in_range(client, chain_tip, fetch_count)

        if not blocks:
            logger.warning("Fetch returned no blocks.")
            return 0

        # 4. Bulk insert
        inserted = await _bulk_insert_blocks(blocks)

        height_range = f"{blocks[-1].height}..{blocks[0].height}"
        logger.info(
            f"Backfill complete: {inserted} blocks inserted "
            f"(heights {height_range})"
        )
        return inserted


async def main() -> None:
    """CLI entry point for manual backfill."""
    logger.info("Starting incremental backfill...")
    inserted = await incremental_backfill()
    logger.info(f"Done. {inserted} blocks inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
