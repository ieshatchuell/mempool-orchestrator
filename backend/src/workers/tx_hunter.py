"""Advisory Engine — scans for stuck mempool transactions and writes RBF/CPFP advisories.

Polls the mempool.space REST API for recent transactions, identifies those
with fee rates significantly below the current median, and generates
actionable RBF/CPFP cost estimates written to the PostgreSQL advisories table.

Can be invoked:
- As a standalone worker: `python -m src.workers.tx_hunter`
- Via Justfile: `just hunter`

Design:
- Polling interval: 60 seconds
- Source: GET /api/mempool/recent (external API)
- Target: PostgreSQL `advisories` table (via AdvisoryRecord ORM)
- Formulas: BIP-125 (RBF), Package Relay (CPFP) — see .agent/skills/bitcoin/SKILL.md
"""

import asyncio
import math

import httpx
from loguru import logger
from sqlalchemy import select, desc, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.config import settings
from src.infrastructure.database.session import engine, async_session
from src.infrastructure.database.models import Base, MempoolSnapshot, AdvisoryRecord

# ── Configuration ────────────────────────────────────────────────

POLL_INTERVAL_SECONDS = 60
MAX_RECENT_TXS = 50
STUCK_THRESHOLD_RATIO = 0.5  # fee_rate < median * 0.5 → "stuck"
MAX_ADVISORIES = 10  # Keep top N most stuck txs per cycle
DEFAULT_CHILD_VSIZE = 141  # Typical 1-in-1-out child tx (P2WPKH)


# ── Fee Calculation (BIP-125 RBF + Package Relay CPFP) ───────────


def calculate_rbf_fee(
    original_fee: int,
    original_vsize: float,
    target_fee_rate: float,
) -> int:
    """Calculate the total fee needed for an RBF replacement transaction.

    BIP-125 Rules:
    1. NewFee > OriginalFee (absolute fee rule)
    2. NewFeeRate >= OriginalFeeRate + MinRelayTxFee (relay fee rule)

    Args:
        original_fee: Current tx fee in satoshis.
        original_vsize: Current tx virtual size in vBytes.
        target_fee_rate: Market target fee rate in sat/vB.

    Returns:
        Total fee the replacement tx should pay (satoshis).
    """
    # Enforce both BIP-125 rules
    original_fee_rate = original_fee / max(original_vsize, 1)
    min_rbf_rate = max(target_fee_rate, original_fee_rate + 1.0)
    rbf_fee = math.ceil(min_rbf_rate * original_vsize)

    # Must be strictly greater than original fee
    return max(rbf_fee, original_fee + 1)


def calculate_cpfp_fee(
    parent_fee: int,
    parent_vsize: float,
    target_fee_rate: float,
    child_vsize: float = DEFAULT_CHILD_VSIZE,
) -> int:
    """Calculate the fee a child transaction must pay for CPFP.

    Package Relay formula:
    PackageFeeRate = (ParentFee + ChildFee) / (ParentVSize + ChildVSize)
    Solving for ChildFee:
    ChildFee = (TargetRate * (ParentVSize + ChildVSize)) - ParentFee

    Args:
        parent_fee: Parent tx fee in satoshis.
        parent_vsize: Parent tx virtual size in vBytes.
        target_fee_rate: Market target fee rate in sat/vB.
        child_vsize: Assumed child tx size (default: 141 vB for P2WPKH).

    Returns:
        Fee the child tx must pay (satoshis). Minimum 1 sat.
    """
    package_size = parent_vsize + child_vsize
    child_fee = math.ceil(target_fee_rate * package_size) - parent_fee
    return max(child_fee, 1)


# ── Data Fetching ────────────────────────────────────────────────


async def _fetch_recent_txs(client: httpx.AsyncClient) -> list[dict]:
    """Fetch recent mempool transactions from mempool.space REST API.

    GET /api/mempool/recent returns the last ~10 transactions entering the mempool.
    """
    url = f"{settings.mempool_api_url}/mempool/recent"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        txs = resp.json()
        if isinstance(txs, list):
            return txs[:MAX_RECENT_TXS]
        return []
    except Exception as e:
        logger.error(f"Failed to fetch recent txs: {e}")
        return []


async def _get_current_median_fee() -> float:
    """Get the current median fee from the latest mempool snapshot."""
    async with async_session() as session:
        result = await session.execute(
            select(MempoolSnapshot.median_fee)
            .order_by(desc(MempoolSnapshot.captured_at))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row if row and row > 0 else 1.0


# ── Advisory Logic ───────────────────────────────────────────────


def _classify_tx(
    tx: dict,
    current_median_fee: float,
) -> dict | None:
    """Classify a transaction as stuck and generate advisory data.

    A transaction is considered stuck if its fee rate is below
    STUCK_THRESHOLD_RATIO * current_median_fee.

    Returns:
        Advisory dict or None if tx is not stuck.
    """
    txid = tx.get("txid")
    fee = tx.get("fee")
    vsize = tx.get("vsize")

    if not txid or fee is None or vsize is None:
        return None
    if vsize <= 0:
        return None

    fee_rate = fee / vsize
    threshold = current_median_fee * STUCK_THRESHOLD_RATIO

    if fee_rate >= threshold:
        return None  # Not stuck

    # Target: current median (aim for next-block confirmation)
    target_fee_rate = max(current_median_fee, 1.0)

    rbf_fee = calculate_rbf_fee(fee, vsize, target_fee_rate)
    cpfp_fee = calculate_cpfp_fee(fee, vsize, target_fee_rate)

    return {
        "txid": txid,
        "action": "BUMP",
        "current_fee_rate": round(fee_rate, 4),
        "target_fee_rate": round(target_fee_rate, 4),
        "rbf_fee_sats": rbf_fee,
        "cpfp_fee_sats": cpfp_fee,
    }


# ── Database Operations ──────────────────────────────────────────


async def _persist_advisories(advisories: list[dict]) -> int:
    """Write advisories to PostgreSQL with upsert (ON CONFLICT by txid).

    Clears old advisories first (rotating showcase pattern).

    Returns:
        Number of advisories persisted.
    """
    if not advisories:
        return 0

    async with async_session() as session:
        # Clear previous cycle's advisories
        await session.execute(delete(AdvisoryRecord))

        # Insert new advisories
        stmt = pg_insert(AdvisoryRecord).values(advisories)
        await session.execute(stmt)
        await session.commit()

    return len(advisories)


# ── Main Loop ────────────────────────────────────────────────────


async def run_advisory_cycle() -> int:
    """Execute one advisory scan cycle.

    Returns:
        Number of advisories generated.
    """
    current_median_fee = await _get_current_median_fee()
    logger.info(f"Current median fee: {current_median_fee:.2f} sat/vB")

    async with httpx.AsyncClient(timeout=30) as client:
        recent_txs = await _fetch_recent_txs(client)

    if not recent_txs:
        logger.debug("No recent transactions found.")
        return 0

    # Classify transactions
    candidates = []
    for tx in recent_txs:
        advisory = _classify_tx(tx, current_median_fee)
        if advisory:
            candidates.append(advisory)

    if not candidates:
        logger.info("No stuck transactions detected this cycle.")
        return 0

    # Sort by fee_rate ascending (most stuck first), keep top N
    candidates.sort(key=lambda x: x["current_fee_rate"])
    top_candidates = candidates[:MAX_ADVISORIES]

    # Persist to PostgreSQL
    inserted = await _persist_advisories(top_candidates)
    logger.info(
        f"🕵️ Advisory Engine: {inserted} advisories written "
        f"(threshold: {current_median_fee * STUCK_THRESHOLD_RATIO:.2f} sat/vB)"
    )
    return inserted


async def main() -> None:
    """Main polling loop — runs advisory cycles every POLL_INTERVAL_SECONDS."""
    # DDL bootstrap
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Advisory Engine DDL bootstrap complete.")

    logger.info(
        f"🕵️ Advisory Engine started "
        f"(poll: {POLL_INTERVAL_SECONDS}s, threshold: {STUCK_THRESHOLD_RATIO}x median)"
    )

    try:
        while True:
            try:
                await run_advisory_cycle()
            except Exception as e:
                logger.error(f"Advisory cycle failed: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Advisory Engine stopped.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
