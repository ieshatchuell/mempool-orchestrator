"""Automated Showcase Hunter for tracking interesting mempool transactions.

Filters recent mempool transactions and adds them to the watchlist if they
are considered 'stuck' or 'interesting' (e.g., fee rate significantly below
the current network median).
"""

from loguru import logger
from src.ingestors.mempool_api import MempoolAPI
from src.storage.watchlist import Watchlist, WatchlistEntry


async def run_showcase_hunter(api: MempoolAPI, watchlist: Watchlist, current_median_fee: float) -> None:
    """Scan recent mempool transactions and rotate the top 5 stuck ones.
    
    A transaction is considered a candidate for the showcase if its 
    fee rate is less than half of the current median fee.
    
    Args:
        api: Authorized MempoolAPI client.
        watchlist: The Watchlist DuckDB storage connection.
        current_median_fee: The current median fee in sat/vB.
    """
    try:
        # 1. Fetch recent transactions entering the mempool
        recent_txs = await api.get_recent_mempool_txs()
        if not recent_txs:
            logger.debug("Showcase Hunter: No recent transactions found.")
            return

        target_fee_rate = max(5.0, current_median_fee * 0.8)
        candidates = []

        # 2. Filter for stuck candidates
        for tx in recent_txs:
            fee = tx.get("fee")
            vsize = tx.get("vsize")
            txid = tx.get("txid")
            
            if fee is None or vsize is None or not txid:
                continue

            # Ensure we don't divide by zero
            if vsize <= 0:
                continue

            fee_rate = fee / vsize
            if fee_rate < target_fee_rate:
                candidates.append({
                    "txid": txid,
                    "fee": fee,
                    "fee_rate": fee_rate,
                })

        if not candidates:
            return

        # 3. Sort by fee_rate ascending (most stuck first), take Top 5
        candidates.sort(key=lambda x: x["fee_rate"])
        top_candidates = candidates[:5]

        # 4. Rotate the showcase
        deleted = watchlist.clear_active()
        
        inserted = 0
        for cand in top_candidates:
            entry = WatchlistEntry(txid=cand["txid"])
            success = watchlist.add_tx(entry, fee=cand["fee"], fee_rate=cand["fee_rate"])
            if success:
                inserted += 1

        logger.info(f"🕵️ Showcase Hunter: Rotated {deleted} old items, found {inserted} new stuck transactions.")

    except Exception as e:
        logger.warning(f"⚠️ Showcase Hunter failed: {type(e).__name__}: {e}")
