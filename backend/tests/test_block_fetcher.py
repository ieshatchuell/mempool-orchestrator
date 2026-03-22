"""Unit tests for Block Fetcher worker (ADR-024).

Tests verify the handle_block_signal function correctly:
  - Fetches block data via REST and produces to mempool-raw
  - Handles fetch failures gracefully (no Kafka production)
  - Skips invalid signal payloads
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.schemas import ConfirmedBlock, ConfirmedBlockExtras
from src.workers.block_fetcher import handle_block_signal


# =============================================================================
# Block Signal Processing
# =============================================================================


class TestHandleBlockSignal:
    """Test suite for block signal processing with mocked HTTP + Kafka."""

    @pytest.mark.asyncio
    @patch("src.workers.block_fetcher.fetch_confirmed_block")
    async def test_fetch_and_produce(self, mock_fetch):
        """Valid signal triggers REST fetch and Kafka production."""
        mock_producer = AsyncMock()

        mock_block = ConfirmedBlock(
            id="00000000000000000001abcdef",
            height=800000,
            timestamp=1706500000,
            size=1500000,
            tx_count=3000,
            extras=ConfirmedBlockExtras(
                virtual_size=997892.5,
                total_fees=2036508,
                median_fee=5.0,
                fee_range=[1.0, 2.0, 5.0, 10.0],
                pool={"name": "Foundry USA"},
            ),
        )
        mock_fetch.return_value = mock_block

        signal_payload = json.dumps({
            "hash": "00000000000000000001abcdef",
            "height": 800000,
        }).encode("utf-8")

        await handle_block_signal(signal_payload, mock_producer)

        # Assert fetch was called with the block hash
        mock_fetch.assert_called_once_with("00000000000000000001abcdef")

        # Assert producer.send was called with confirmed_block key
        assert mock_producer.send.call_count == 1
        call_kwargs = mock_producer.send.call_args.kwargs
        assert call_kwargs["key"] == "confirmed_block"

    @pytest.mark.asyncio
    @patch("src.workers.block_fetcher.fetch_confirmed_block")
    async def test_fetch_failure_no_produce(self, mock_fetch):
        """When REST fetch fails, no message is produced to Kafka."""
        mock_producer = AsyncMock()
        mock_fetch.return_value = None  # Fetch failed

        signal_payload = json.dumps({
            "hash": "00000000000000000001234567890abcdef",
            "height": 800000,
        }).encode("utf-8")

        await handle_block_signal(signal_payload, mock_producer)

        mock_fetch.assert_called_once()
        mock_producer.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_json_skipped(self):
        """Malformed JSON payload is logged and skipped (no crash)."""
        mock_producer = AsyncMock()

        await handle_block_signal(b"not-valid-json{{{", mock_producer)

        mock_producer.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_hash_skipped(self):
        """Signal payload without 'hash' field is skipped."""
        mock_producer = AsyncMock()

        signal_payload = json.dumps({
            "height": 800000,
        }).encode("utf-8")

        await handle_block_signal(signal_payload, mock_producer)

        mock_producer.send.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.workers.block_fetcher.fetch_confirmed_block")
    async def test_produced_payload_is_valid_json(self, mock_fetch):
        """The payload sent to Kafka is valid JSON representing a ConfirmedBlock."""
        mock_producer = AsyncMock()

        mock_block = ConfirmedBlock(
            id="00000000000000000002bcdef0",
            height=900001,
            timestamp=1710000000,
            size=1400000,
            tx_count=2500,
            extras=ConfirmedBlockExtras(
                virtual_size=950000.0,
                total_fees=1800000,
                median_fee=4.0,
                fee_range=[0.5, 1.0, 3.0, 8.0],
                pool={"name": "AntPool"},
            ),
        )
        mock_fetch.return_value = mock_block

        signal_payload = json.dumps({
            "hash": "00000000000000000002bcdef0",
            "height": 900001,
        }).encode("utf-8")

        await handle_block_signal(signal_payload, mock_producer)

        # Verify the payload is valid JSON and contains expected fields
        call_kwargs = mock_producer.send.call_args.kwargs
        payload = json.loads(call_kwargs["value"].decode("utf-8"))
        assert payload["id"] == "00000000000000000002bcdef0"
        assert payload["height"] == 900001
        assert payload["tx_count"] == 2500
