"""Unit tests for Bitcoin data contract schemas.

Tests validate Pydantic models for MempoolStats and MempoolBlock with both
valid and invalid data, ensuring proper camelCase ↔ snake_case mapping and
strict type enforcement.
"""

import pytest
from pydantic import ValidationError

from src.domain.schemas import MempoolStats, MempoolBlock, MempoolInfo


class TestMempoolStats:
    """Test suite for MempoolStats schema validation."""

    def test_valid_mempool_stats(self):
        """Verify MempoolStats parses valid camelCase data correctly."""
        # Simulate WebSocket payload from Mempool.space API
        data = {
            "mempoolInfo": {
                "size": 150000,
                "bytes": 75000000,
                "usage": 250000000,
                "totalFee": 1.5,
                "mempoolMinFee": 0.00001,
                "minRelayTxFee": 0.00001
            }
        }
        
        # Validate parsing
        stats = MempoolStats.model_validate(data)
        
        # Assert field mapping (camelCase → snake_case)
        assert stats.mempool_info.size == 150000
        assert stats.mempool_info.bytes == 75000000
        assert stats.mempool_info.usage == 250000000
        assert stats.mempool_info.total_fee == 150_000_000  # 1.5 BTC → Satoshis
        assert stats.mempool_info.mempool_min_fee == 0.00001
        assert stats.mempool_info.min_relay_tx_fee == 0.00001

    def test_valid_mempool_stats_with_optional_fields_missing(self):
        """Verify MempoolStats handles missing optional fields gracefully."""
        data = {
            "mempoolInfo": {
                "size": 100000,
                "bytes": 50000000,
                "totalFee": 2.0
            }
        }
        
        stats = MempoolStats.model_validate(data)
        
        assert stats.mempool_info.size == 100000
        assert stats.mempool_info.bytes == 50000000
        assert stats.mempool_info.total_fee == 200_000_000  # 2.0 BTC → Satoshis
        assert stats.mempool_info.usage is None
        assert stats.mempool_info.mempool_min_fee is None
        assert stats.mempool_info.min_relay_tx_fee is None


class TestMempoolBlock:
    """Test suite for MempoolBlock schema validation."""

    def test_valid_mempool_block(self):
        """Verify MempoolBlock parses valid projected block data correctly."""
        # Simulate mempool-blocks WebSocket payload
        data = {
            "blockSize": 1500000,
            "blockVSize": 999817,
            "nTx": 2500,
            "totalFees": 50000000,
            "medianFee": 15.5,
            "feeRange": [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0]
        }
        
        # Validate parsing
        block = MempoolBlock.model_validate(data)
        
        # Assert field mapping (camelCase → snake_case)
        assert block.block_size == 1500000
        assert block.block_v_size == 999817
        assert block.n_tx == 2500
        assert block.total_fees == 50000000
        assert block.median_fee == 15.5
        assert block.fee_range == [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0]

    def test_mempool_block_fee_range_empty(self):
        """Verify MempoolBlock handles empty fee_range list."""
        data = {
            "blockSize": 1000000,
            "blockVSize": 750000,
            "nTx": 1000,
            "totalFees": 25000000,
            "medianFee": 10.0,
            "feeRange": []
        }
        
        block = MempoolBlock.model_validate(data)
        assert block.fee_range == []


class TestSchemaValidation:
    """Test suite for schema type enforcement and error handling."""

    def test_invalid_type_total_fees_string(self):
        """Verify ValidationError is raised for invalid totalFees type."""
        # totalFees should be int, but we pass a string
        data = {
            "blockSize": 1500000,
            "blockVSize": 999817,
            "nTx": 2500,
            "totalFees": "bad",  # Invalid: string instead of int
            "medianFee": 15.5,
            "feeRange": [1.0, 5.0, 10.0]
        }
        
        # Assert Pydantic raises ValidationError
        with pytest.raises(ValidationError) as exc_info:
            MempoolBlock.model_validate(data)
        
        # Verify error contains information about totalFees field
        error_msg = str(exc_info.value).lower()
        assert "totalfees" in error_msg or "total_fees" in error_msg

    def test_invalid_type_mempool_info_size(self):
        """Verify ValidationError is raised for invalid size type in MempoolInfo."""
        data = {
            "mempoolInfo": {
                "size": "not_an_int",  # Invalid: string instead of int
                "bytes": 50000000,
                "totalFee": 1.5
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MempoolStats.model_validate(data)
        
        # Verify error contains information about size field
        assert "size" in str(exc_info.value).lower()

    def test_missing_required_field(self):
        """Verify ValidationError is raised when required fields are missing."""
        # Missing required field 'medianFee'
        data = {
            "blockSize": 1500000,
            "blockVSize": 999817,
            "nTx": 2500,
            "totalFees": 50000000,
            "feeRange": [1.0, 5.0, 10.0]
            # medianFee is missing
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MempoolBlock.model_validate(data)
        
        # Verify error mentions the missing field
        error_msg = str(exc_info.value).lower()
        assert "medianfee" in error_msg or "median_fee" in error_msg


class TestAliasMapping:
    """Test suite for camelCase ↔ snake_case alias mapping."""

    def test_mempool_info_populate_by_name(self):
        """Verify populate_by_name allows both camelCase and snake_case."""
        # Test with snake_case input (should work due to populate_by_name=True)
        data_snake = {
            "size": 100000,
            "bytes": 50000000,
            "total_fee": 2.0
        }
        
        info = MempoolInfo.model_validate(data_snake)
        assert info.total_fee == 200_000_000  # 2.0 BTC → Satoshis
        
        # Test with camelCase input (default from API)
        data_camel = {
            "size": 100000,
            "bytes": 50000000,
            "totalFee": 3.0
        }
        
        info_camel = MempoolInfo.model_validate(data_camel)
        assert info_camel.total_fee == 300_000_000  # 3.0 BTC → Satoshis

    def test_total_fee_btc_to_satoshis_conversion(self):
        """Verify total_fee is converted from BTC float to Satoshis integer at ingestion."""
        data = {
            "size": 100000,
            "bytes": 50000000,
            "totalFee": 0.29999999,  # Edge case: float precision
        }
        info = MempoolInfo.model_validate(data)
        assert isinstance(info.total_fee, int)
        assert info.total_fee == 29999999  # round(0.29999999 * 1e8) = 29999999

    def test_total_fee_accepts_integer_directly(self):
        """Verify total_fee accepts pre-converted Satoshi integers."""
        data = {
            "size": 100000,
            "bytes": 50000000,
            "total_fee": 150_000_000,  # Already Satoshis
        }
        info = MempoolInfo.model_validate(data)
        assert info.total_fee == 150_000_000

    def test_mempool_block_serialization_to_camel(self):
        """Verify model serialization converts back to camelCase for API compatibility."""
        data = {
            "blockSize": 1500000,
            "blockVSize": 999817,
            "nTx": 2500,
            "totalFees": 50000000,
            "medianFee": 15.5,
            "feeRange": [1.0, 5.0, 10.0]
        }
        
        block = MempoolBlock.model_validate(data)
        
        # Serialize back to dict with aliases (camelCase)
        serialized = block.model_dump(by_alias=True)
        
        assert "blockSize" in serialized
        assert "blockVSize" in serialized
        assert "nTx" in serialized
        assert "totalFees" in serialized
        assert "medianFee" in serialized
        assert "feeRange" in serialized

    # ── ADR-021: median_fee Default ──────────────────────────────

    def test_mempool_info_median_fee_default(self):
        """ADR-021: MempoolInfo without medianFee defaults to 1.0 (MinRelayTxFee)."""
        data = {
            "size": 100000,
            "bytes": 50000000,
            "totalFee": 1.0,
        }
        info = MempoolInfo.model_validate(data)
        assert info.median_fee == 1.0  # Default fallback

    def test_mempool_info_median_fee_enriched(self):
        """ADR-021: MempoolInfo with medianFee uses the provided value."""
        data = {
            "size": 100000,
            "bytes": 50000000,
            "totalFee": 1.0,
            "medianFee": 12.5,
        }
        info = MempoolInfo.model_validate(data)
        assert info.median_fee == 12.5