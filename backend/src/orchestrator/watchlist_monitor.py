"""Watchlist monitor — polls mempool.space REST API for tx confirmation status.

Non-blocking polling loop that runs alongside the orchestrator's decision cycle.
For each PENDING tx in the watchlist, checks `GET /api/tx/{txid}` and updates
status to CONFIRMED when mined.

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


async def check_watchlist(watchlist: Watchlist) -> int:
    """Poll mempool.space for status updates on all PENDING transactions.
    
    For each PENDING tx:
    1. GET /api/tx/{txid} from mempool.space
    2. If status.confirmed == true → mark_confirmed() in DB
    3. If API error → skip (will retry next cycle)
    
    Args:
        watchlist: Watchlist persistence instance.
        
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
                logger.debug(
                    f"   ⏳ {entry.txid[:16]}... still pending "
                    f"(role={entry.role})"
                )
                
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


async def close_client() -> None:
    """Close the shared httpx client on shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
