"""Watchlist monitor — polls mempool.space REST API for tx confirmation status.

Non-blocking polling loop that runs alongside the orchestrator's decision cycle.
For each PENDING tx in the watchlist, checks `GET /api/tx/{txid}` and updates
status to CONFIRMED when mined.

Phase 3 Addition:
- RBF Advisor (SENDER): If tx is stuck, calculates optimal replacement fee (BIP-125).
- CPFP Advisor (RECEIVER): If tx is stuck, calculates child fee to unstick (Package Relay).
- Both advisors use `target_fee_rate` from `evaluate_market_rules()` to respect
  the active strategy mode (PATIENT/RELIABLE).

Design:
- Uses httpx async client for non-blocking HTTP
- Rate-limited: processes one tx per call to avoid API abuse
- Silent failures: logs warnings but never raises (non-critical path)
- Integrates via `check_watchlist()` called from the orchestrator loop
"""

import httpx
from loguru import logger

from src.config import settings
from src.storage.watchlist import Watchlist
from src.strategies.advisors import evaluate_rbf, evaluate_cpfp


# Shared httpx client (lazy init)
_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.mempool_api_url,
            timeout=15.0,
        )
    return _client


async def check_watchlist(watchlist: Watchlist, target_fee_rate: float = 1.0) -> int:
    """Poll mempool.space for status updates on all PENDING transactions.
    
    For each PENDING tx:
    1. GET /api/tx/{txid} from mempool.space
    2. If status.confirmed == true → mark_confirmed() in DB
    3. If still pending → run RBF/CPFP advisor based on role
    4. If API error → skip (will retry next cycle)
    
    Args:
        watchlist: Watchlist persistence instance.
        target_fee_rate: Recommended fee rate from evaluate_market_rules().
            Used as the target for RBF/CPFP calculations. Defaults to 1.0
            (minrelaytxfee) if not provided.
        
    Returns:
        Number of newly confirmed transactions this cycle.
    """
    active = watchlist.get_active()
    
    if not active:
        return 0
    
    client = await _get_client()
    confirmed_count = 0
    
    logger.debug(f"👁️ Watchlist: Checking {len(active)} pending transaction(s)")
    
    for entry in active:
        try:
            response = await client.get(f"/api/tx/{entry.txid}")
            response.raise_for_status()
            
            tx_data = response.json()
            status = tx_data.get("status", {})
            
            if status.get("confirmed", False):
                block_height = status.get("block_height", 0)
                watchlist.mark_confirmed(entry.txid, block_height)
                confirmed_count += 1
            else:
                # Tx still pending — run fee advisor
                _run_advisor(entry, tx_data, target_fee_rate)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    f"   ❓ {entry.txid[:16]}... not found (dropped from mempool?)"
                )
            else:
                logger.warning(
                    f"   ⚠️ {entry.txid[:16]}... API error: {e.response.status_code}"
                )
        except httpx.RequestError as e:
            logger.warning(f"   ⚠️ Watchlist API unreachable: {e}")
            break  # Don't hammer a down API
    
    if confirmed_count > 0:
        logger.success(
            f"🎯 Watchlist: {confirmed_count} tx(s) confirmed this cycle "
            f"({watchlist.count_active()} still pending)"
        )
    
    return confirmed_count


def _run_advisor(entry, tx_data: dict, target_fee_rate: float) -> None:
    """Run both fee advisors (RBF + CPFP) for a pending transaction.
    
    Extracts fee and vsize from the API response and runs both advisors.
    No role required — the user interprets which advice applies.
    
    Non-critical: all errors are caught and logged as warnings.
    
    Args:
        entry: WatchlistRecord with txid, etc.
        tx_data: Raw JSON response from GET /api/tx/{txid}.
        target_fee_rate: Target fee rate from evaluate_market_rules().
    """
    try:
        fee_sats = tx_data.get("fee")
        weight = tx_data.get("weight")
        
        if fee_sats is None or weight is None:
            logger.debug(
                f"   ⏳ {entry.txid[:16]}... still pending "
                f"(missing fee/weight data)"
            )
            return
        
        # vsize = weight / 4 (BIP-141)
        vsize = weight / 4.0
        if vsize <= 0:
            return
        
        fee_rate = fee_sats / vsize
        
        # Run BOTH advisors for every transaction
        rbf = evaluate_rbf(
            original_fee_sats=fee_sats,
            original_fee_rate=fee_rate,
            original_vsize=vsize,
            target_fee_rate=target_fee_rate,
        )
        cpfp = evaluate_cpfp(
            parent_fee_sats=fee_sats,
            parent_vsize=vsize,
            target_fee_rate=target_fee_rate,
        )
        
        if rbf.is_stuck:
            logger.warning(
                f"   🔄 RBF: {entry.txid[:16]}... stuck at "
                f"{fee_rate:.1f} sat/vB → "
                f"recommend {rbf.target_fee_rate:.1f} sat/vB "
                f"({rbf.target_fee_sats} sats total)"
            )
            logger.warning(
                f"   ⚡ CPFP: {entry.txid[:16]}... → "
                f"child fee needed: {cpfp.child_fee_sats} sats "
                f"(package rate: {cpfp.package_fee_rate:.1f} sat/vB)"
            )
        else:
            logger.debug(
                f"   ✅ {entry.txid[:16]}... fee OK at "
                f"{fee_rate:.1f} sat/vB (target: {target_fee_rate:.1f})"
            )
    except Exception as e:
        logger.warning(
            f"   ⚠️ Advisor failed for {entry.txid[:16]}...: "
            f"{type(e).__name__}: {e}"
        )


async def close_client() -> None:
    """Close the shared httpx client on shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
