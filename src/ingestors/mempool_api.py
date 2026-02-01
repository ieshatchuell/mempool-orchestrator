"""REST API client for Mempool.space.

Provides async HTTP methods to fetch block statistics and transaction data
from the Mempool.space public API.
"""

import httpx
from typing import Dict, Any

from src.config import settings


class MempoolAPIError(Exception):
    """Raised when the Mempool.space API returns an error or network failure occurs."""
    pass


class MempoolAPI:
    """Async HTTP client for Mempool.space REST API.
    
    Usage:
        async with MempoolAPI() as api:
            block_data = await api.get_block_stats("block_hash_here")
    """

    def __init__(self):
        """Initialize the API client with base URL from settings."""
        self.base_url = settings.mempool_api_url
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry - creates the HTTP client."""
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes the HTTP client."""
        if self.client:
            await self.client.aclose()

    async def get_block_stats(self, block_hash: str) -> Dict[str, Any]:
        """Fetch block header statistics from the API.
        
        Args:
            block_hash: The block hash (hex string).
            
        Returns:
            Dictionary containing block header data (id, height, version, timestamp, etc.).
            
        Raises:
            MempoolAPIError: If the request fails (4xx, 5xx, network error, or invalid JSON).
        """
        if not self.client:
            raise MempoolAPIError("Client not initialized. Use 'async with MempoolAPI()' context manager.")

        endpoint = f"/block/{block_hash}"
        
        try:
            response = await self.client.get(endpoint)
            
            # Check for HTTP errors
            if response.status_code == 404:
                raise MempoolAPIError(f"Block not found: {block_hash} (HTTP 404)")
            elif response.status_code >= 500:
                raise MempoolAPIError(f"Server error: HTTP {response.status_code}")
            elif response.status_code >= 400:
                raise MempoolAPIError(f"Client error: HTTP {response.status_code}")
            
            # Parse JSON response
            try:
                return response.json()
            except Exception as e:
                raise MempoolAPIError(f"Failed to parse JSON response: {e}")
                
        except httpx.RequestError as e:
            raise MempoolAPIError(f"Network error: {e}")
        except MempoolAPIError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            raise MempoolAPIError(f"Unexpected error: {e}")
