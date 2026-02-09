"""Unit tests for Mempool.space REST API client.

Tests validate the MempoolAPI wrapper behavior using respx to mock
HTTP requests without making real network calls.
"""

import pytest
import respx
import httpx
from unittest.mock import patch

from src.ingestors.mempool_api import MempoolAPI, MempoolAPIError


class TestMempoolAPIInitialization:
    """Test suite for MempoolAPI initialization."""

    def test_api_uses_settings_base_url(self):
        """Verify API client uses base URL from settings."""
        api = MempoolAPI()
        
        # Should use the default from settings
        assert api.base_url == "https://mempool.space/api/v1"

    @patch('src.ingestors.mempool_api.settings')
    def test_api_respects_custom_base_url(self, mock_settings):
        """Verify API client respects custom base URL from settings."""
        mock_settings.mempool_api_url = "https://custom.mempool.space/api/v2"
        
        api = MempoolAPI()
        assert api.base_url == "https://custom.mempool.space/api/v2"

    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self):
        """Verify async context manager initializes httpx client."""
        async with MempoolAPI() as api:
            assert api.client is not None
            assert isinstance(api.client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        """Verify async context manager closes httpx client on exit."""
        api = MempoolAPI()
        async with api:
            client = api.client
            assert client is not None
        
        # After exiting context, client should be closed
        assert client.is_closed


class TestGetBlockStats:
    """Test suite for get_block_stats method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_block_fetch(self):
        """Verify successful block data retrieval (200 OK)."""
        # Mock response data
        mock_block_data = {
            "id": "00000000000000000001c1c2f8f3d5e4",
            "height": 800000,
            "version": 536870912,
            "timestamp": 1689000000,
            "tx_count": 2500,
            "size": 1500000,
            "weight": 4000000,
        }
        
        # Mock the HTTP request
        respx.get("https://mempool.space/api/v1/block/00000000000000000001c1c2f8f3d5e4").mock(
            return_value=httpx.Response(200, json=mock_block_data)
        )
        
        async with MempoolAPI() as api:
            result = await api.get_block_stats("00000000000000000001c1c2f8f3d5e4")
        
        assert result == mock_block_data
        assert result["height"] == 800000
        assert result["tx_count"] == 2500

    @pytest.mark.asyncio
    @respx.mock
    async def test_block_not_found_404(self):
        """Verify 404 raises MempoolAPIError."""
        # Mock 404 response
        respx.get("https://mempool.space/api/v1/block/invalid_hash").mock(
            return_value=httpx.Response(404)
        )
        
        async with MempoolAPI() as api:
            with pytest.raises(MempoolAPIError) as exc_info:
                await api.get_block_stats("invalid_hash")
        
        assert "Block not found" in str(exc_info.value)
        assert "HTTP 404" in str(exc_info.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_error_500(self):
        """Verify 500 raises MempoolAPIError."""
        # Mock 500 response
        respx.get("https://mempool.space/api/v1/block/some_hash").mock(
            return_value=httpx.Response(500)
        )
        
        async with MempoolAPI() as api:
            with pytest.raises(MempoolAPIError) as exc_info:
                await api.get_block_stats("some_hash")
        
        assert "Server error" in str(exc_info.value)
        assert "HTTP 500" in str(exc_info.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_client_error_400(self):
        """Verify 4xx errors raise MempoolAPIError."""
        # Mock 400 response
        respx.get("https://mempool.space/api/v1/block/bad_request").mock(
            return_value=httpx.Response(400)
        )
        
        async with MempoolAPI() as api:
            with pytest.raises(MempoolAPIError) as exc_info:
                await api.get_block_stats("bad_request")
        
        assert "Client error" in str(exc_info.value)
        assert "HTTP 400" in str(exc_info.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_network_timeout_error(self):
        """Verify network errors raise MempoolAPIError."""
        # Mock network timeout
        respx.get("https://mempool.space/api/v1/block/timeout_test").mock(
            side_effect=httpx.RequestError("Connection timeout")
        )
        
        async with MempoolAPI() as api:
            with pytest.raises(MempoolAPIError) as exc_info:
                await api.get_block_stats("timeout_test")
        
        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_invalid_json_response(self):
        """Verify invalid JSON raises MempoolAPIError."""
        # Mock response with invalid JSON
        respx.get("https://mempool.space/api/v1/block/bad_json").mock(
            return_value=httpx.Response(200, text="Not valid JSON {]")
        )
        
        async with MempoolAPI() as api:
            with pytest.raises(MempoolAPIError) as exc_info:
                await api.get_block_stats("bad_json")
        
        assert "Failed to parse JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_client_not_initialized_error(self):
        """Verify calling methods outside context manager raises error."""
        api = MempoolAPI()
        
        with pytest.raises(MempoolAPIError) as exc_info:
            await api.get_block_stats("some_hash")
        
        assert "Client not initialized" in str(exc_info.value)
        assert "context manager" in str(exc_info.value)


class TestIntegrationScenarios:
    """Test suite for realistic usage scenarios."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_multiple_requests_in_same_session(self):
        """Verify multiple requests can be made in the same session."""
        # Mock two different blocks
        respx.get("https://mempool.space/api/v1/block/hash1").mock(
            return_value=httpx.Response(200, json={"height": 1})
        )
        respx.get("https://mempool.space/api/v1/block/hash2").mock(
            return_value=httpx.Response(200, json={"height": 2})
        )
        
        async with MempoolAPI() as api:
            result1 = await api.get_block_stats("hash1")
            result2 = await api.get_block_stats("hash2")
        
        assert result1["height"] == 1
        assert result2["height"] == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_error_doesnt_crash_session(self):
        """Verify one failed request doesn't prevent subsequent requests."""
        # First request fails, second succeeds
        respx.get("https://mempool.space/api/v1/block/fail").mock(
            return_value=httpx.Response(404)
        )
        respx.get("https://mempool.space/api/v1/block/success").mock(
            return_value=httpx.Response(200, json={"height": 100})
        )
        
        async with MempoolAPI() as api:
            # First request should fail
            with pytest.raises(MempoolAPIError):
                await api.get_block_stats("fail")
            
            # Second request should still work
            result = await api.get_block_stats("success")
            assert result["height"] == 100
