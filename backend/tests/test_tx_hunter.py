"""Unit tests for the Advisory Engine (tx_hunter).

Tests cover:
  - RBF fee calculation (BIP-125 rules)
  - CPFP fee calculation (Package Relay formula)
  - Transaction classification (stuck vs. not stuck)
  - Edge cases (zero values, missing fields)
"""

import pytest

from src.workers.tx_hunter import (
    calculate_rbf_fee,
    calculate_cpfp_fee,
    _classify_tx,
)


# =============================================================================
# RBF Fee Calculation (BIP-125)
# =============================================================================


class TestRbfFeeCalculation:
    """Verify BIP-125 RBF replacement fee calculations."""

    def test_rbf_basic(self):
        """RBF fee is at least target_rate * vsize."""
        result = calculate_rbf_fee(
            original_fee=200,
            original_vsize=200,
            target_fee_rate=5.0,
        )
        # target_rate * vsize = 1000, and must be > original_fee (200)
        assert result >= 1000

    def test_rbf_must_exceed_original_fee(self):
        """RBF fee must be strictly greater than original fee."""
        result = calculate_rbf_fee(
            original_fee=5000,
            original_vsize=200,
            target_fee_rate=5.0,
        )
        assert result > 5000

    def test_rbf_enforces_relay_fee(self):
        """RBF rate must be >= original_rate + 1.0 sat/vB (MinRelayTxFee)."""
        result = calculate_rbf_fee(
            original_fee=1000,
            original_vsize=200,
            target_fee_rate=3.0,  # Below original rate (5.0)
        )
        # Original rate = 5.0, so min_rbf_rate = 5.0 + 1.0 = 6.0
        # RBF fee = 6.0 * 200 = 1200
        assert result >= 1200

    def test_rbf_returns_int(self):
        """Fee is always an integer (satoshis)."""
        result = calculate_rbf_fee(
            original_fee=100,
            original_vsize=141,
            target_fee_rate=2.5,
        )
        assert isinstance(result, int)


# =============================================================================
# CPFP Fee Calculation (Package Relay)
# =============================================================================


class TestCpfpFeeCalculation:
    """Verify Package Relay CPFP child fee calculations."""

    def test_cpfp_basic(self):
        """Child fee compensates for parent's low fee rate."""
        result = calculate_cpfp_fee(
            parent_fee=100,
            parent_vsize=200,
            target_fee_rate=5.0,
            child_vsize=141,
        )
        # Package fee = 5.0 * (200 + 141) = 1705
        # Child fee = 1705 - 100 = 1605
        assert result == 1605

    def test_cpfp_minimum_fee(self):
        """CPFP fee is at least 1 satoshi even if parent overpays."""
        result = calculate_cpfp_fee(
            parent_fee=10000,
            parent_vsize=200,
            target_fee_rate=5.0,
            child_vsize=141,
        )
        assert result >= 1

    def test_cpfp_returns_int(self):
        """Fee is always an integer (satoshis)."""
        result = calculate_cpfp_fee(
            parent_fee=100,
            parent_vsize=200,
            target_fee_rate=3.7,
        )
        assert isinstance(result, int)


# =============================================================================
# Transaction Classification
# =============================================================================


class TestClassifyTx:
    """Verify stuck transaction detection logic."""

    def test_stuck_tx_below_threshold(self):
        """TX with fee_rate < median * 0.5 is classified as stuck."""
        result = _classify_tx(
            tx={"txid": "a" * 64, "fee": 100, "vsize": 200},
            current_median_fee=10.0,
        )
        assert result is not None
        assert result["action"] == "BUMP"
        assert result["txid"] == "a" * 64
        assert result["rbf_fee_sats"] > 0
        assert result["cpfp_fee_sats"] > 0

    def test_normal_tx_above_threshold(self):
        """TX with fee_rate >= median * 0.5 is NOT classified as stuck."""
        result = _classify_tx(
            tx={"txid": "b" * 64, "fee": 2000, "vsize": 200},
            current_median_fee=10.0,
        )
        assert result is None  # fee_rate = 10.0, threshold = 5.0

    def test_missing_fields_returns_none(self):
        """TX with missing required fields returns None."""
        assert _classify_tx(tx={}, current_median_fee=10.0) is None
        assert _classify_tx(tx={"txid": "a" * 64}, current_median_fee=10.0) is None
        assert _classify_tx(tx={"txid": "a" * 64, "fee": 100}, current_median_fee=10.0) is None

    def test_zero_vsize_returns_none(self):
        """TX with vsize=0 returns None (division by zero guard)."""
        result = _classify_tx(
            tx={"txid": "c" * 64, "fee": 100, "vsize": 0},
            current_median_fee=10.0,
        )
        assert result is None
