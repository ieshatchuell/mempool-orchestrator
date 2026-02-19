"""Unit tests for strategies/advisors.py — RBF & CPFP fee advisors.

Pure function tests: no mocks, no I/O, no DuckDB.
All calculations are deterministic and testable with plain values.

Reference:
- RBF: BIP-125 (https://github.com/bitcoin/bips/blob/master/bip-0125.mediawiki)
- CPFP: Bitcoin Ops (https://bitcoinops.org/en/topics/cpfp/)
"""

import math

import pytest

from src.strategies.advisors import (
    ESTIMATED_CHILD_VSIZE,
    MIN_RELAY_FEE_RATE,
    evaluate_rbf,
    evaluate_cpfp,
)


# =============================================================================
# RBF ADVISOR (Sender Strategy)
# =============================================================================


class TestRBFStuckDetection:
    """Detect when a SENDER tx is stuck (fee_rate < target)."""

    def test_stuck_when_rate_below_target(self):
        """Tx paying 2 sat/vB in a 5 sat/vB market → stuck."""
        advice = evaluate_rbf(
            original_fee_sats=400,
            original_fee_rate=2.0,
            original_vsize=200.0,
            target_fee_rate=5.0,
        )
        assert advice.is_stuck is True

    def test_not_stuck_when_rate_equals_target(self):
        """Tx paying exactly the target rate → not stuck."""
        advice = evaluate_rbf(
            original_fee_sats=1000,
            original_fee_rate=5.0,
            original_vsize=200.0,
            target_fee_rate=5.0,
        )
        assert advice.is_stuck is False

    def test_not_stuck_when_rate_above_target(self):
        """Tx paying above the target rate → not stuck."""
        advice = evaluate_rbf(
            original_fee_sats=2000,
            original_fee_rate=10.0,
            original_vsize=200.0,
            target_fee_rate=5.0,
        )
        assert advice.is_stuck is False


class TestRBFRateCalculation:
    """RBF replacement fee rate: max(target, original + 1 sat/vB)."""

    def test_uses_target_when_much_higher(self):
        """Target 10 sat/vB >> original 2 sat/vB → uses target."""
        advice = evaluate_rbf(
            original_fee_sats=400,
            original_fee_rate=2.0,
            original_vsize=200.0,
            target_fee_rate=10.0,
        )
        assert advice.target_fee_rate == 10.0

    def test_uses_original_plus_one_when_close(self):
        """Target 5.0, original 4.5 → uses 4.5 + 1.0 = 5.5 (relay rule)."""
        advice = evaluate_rbf(
            original_fee_sats=900,
            original_fee_rate=4.5,
            original_vsize=200.0,
            target_fee_rate=5.0,
        )
        # max(5.0, 4.5 + 1.0) = 5.5
        assert advice.target_fee_rate == 5.5

    def test_rate_is_max_of_both_rules(self):
        """When original+1 > target, the relay rule wins."""
        advice = evaluate_rbf(
            original_fee_sats=1800,
            original_fee_rate=9.0,
            original_vsize=200.0,
            target_fee_rate=5.0,
        )
        # Not stuck (9.0 >= 5.0), but verify rate formula is correct
        # max(5.0, 9.0 + 1.0) = 10.0
        assert advice.target_fee_rate == 10.0


class TestRBFAbsoluteFeeGuard:
    """BIP-125 Rule 3: new fee (sats) MUST be > original fee (sats)."""

    def test_absolute_fee_strictly_greater(self):
        """target_fee_sats must always be > original_fee_sats."""
        advice = evaluate_rbf(
            original_fee_sats=400,
            original_fee_rate=2.0,
            original_vsize=200.0,
            target_fee_rate=5.0,
        )
        assert advice.target_fee_sats > advice.original_fee_sats

    def test_guard_on_tiny_vsize(self):
        """Small vsize could make ceil(rate * vsize) <= original. Guard must catch it."""
        # original: 100 sats, rate=10, vsize=10
        # target rate = max(11, 10+1) = 11
        # ceil(11 * 10) = 110 > 100 ✓ (natural)
        advice = evaluate_rbf(
            original_fee_sats=100,
            original_fee_rate=10.0,
            original_vsize=10.0,
            target_fee_rate=11.0,
        )
        assert advice.target_fee_sats >= advice.original_fee_sats + 1

    def test_guard_on_edge_case(self):
        """Pathological: very high original fee_sats with low vsize.
        Ensures the max() guard fires when rate*vsize < original+1."""
        # original: 5000 sats, rate=1.0, vsize=100
        # This is unusual (fee_sats doesn't match rate*vsize — simulating API quirks)
        # target rate = max(2.0, 1.0+1.0) = 2.0
        # ceil(2.0 * 100) = 200 < 5001 → guard fires: max(200, 5001) = 5001
        advice = evaluate_rbf(
            original_fee_sats=5000,
            original_fee_rate=1.0,
            original_vsize=100.0,
            target_fee_rate=2.0,
        )
        assert advice.target_fee_sats >= 5001


class TestRBFFloor:
    """Minimum relay fee rate: never recommend below 1 sat/vB."""

    def test_floor_on_zero_target(self):
        """Even if orchestrator says 0, RBF rate must be ≥ 1 sat/vB."""
        advice = evaluate_rbf(
            original_fee_sats=10,
            original_fee_rate=0.1,
            original_vsize=100.0,
            target_fee_rate=0.0,
        )
        assert advice.target_fee_rate >= MIN_RELAY_FEE_RATE


# =============================================================================
# CPFP ADVISOR (Receiver Strategy)
# =============================================================================


class TestCPFPStuckDetection:
    """Detect when a RECEIVER tx is stuck (parent_fee_rate < target)."""

    def test_stuck_when_parent_rate_below_target(self):
        """Parent paying 1 sat/vB in a 5 sat/vB market → stuck."""
        advice = evaluate_cpfp(
            parent_fee_sats=200,
            parent_vsize=200.0,
            target_fee_rate=5.0,
        )
        assert advice.is_stuck is True

    def test_not_stuck_when_parent_rate_at_target(self):
        """Parent paying exactly target → not stuck."""
        advice = evaluate_cpfp(
            parent_fee_sats=1000,
            parent_vsize=200.0,
            target_fee_rate=5.0,
        )
        assert advice.is_stuck is False

    def test_not_stuck_when_parent_rate_above_target(self):
        """Parent paying above target → not stuck."""
        advice = evaluate_cpfp(
            parent_fee_sats=2000,
            parent_vsize=200.0,
            target_fee_rate=5.0,
        )
        assert advice.is_stuck is False


class TestCPFPChildFee:
    """CPFP child fee: ceil(target * (parent_vsize + child_vsize)) - parent_fee."""

    def test_correct_child_fee_calculation(self):
        """Standard case: parent 200 vB, 200 sats, target 5 sat/vB."""
        advice = evaluate_cpfp(
            parent_fee_sats=200,
            parent_vsize=200.0,
            target_fee_rate=5.0,
        )
        # target * (200 + 141) - 200 = 5 * 341 - 200 = 1705 - 200 = 1505
        expected = math.ceil(5.0 * (200.0 + ESTIMATED_CHILD_VSIZE)) - 200
        assert advice.child_fee_sats == expected

    def test_custom_child_vsize(self):
        """Use a custom child vsize instead of the default."""
        advice = evaluate_cpfp(
            parent_fee_sats=200,
            parent_vsize=200.0,
            target_fee_rate=5.0,
            child_vsize=200.0,
        )
        # 5 * (200 + 200) - 200 = 2000 - 200 = 1800
        expected = math.ceil(5.0 * (200.0 + 200.0)) - 200
        assert advice.child_fee_sats == expected


class TestCPFPFloor:
    """Child fee must be at least minrelaytxfee × child_vsize."""

    def test_floor_when_parent_nearly_at_target(self):
        """Parent almost at target → calculated child fee could be tiny.
        Floor ensures child tx is relayable."""
        advice = evaluate_cpfp(
            parent_fee_sats=998,
            parent_vsize=200.0,
            target_fee_rate=5.0,
        )
        # Parent rate = 998/200 = 4.99 sat/vB (barely stuck)
        # Calculated: ceil(5.0 * 341) - 998 = 1705 - 998 = 707
        # Floor: ceil(1.0 * 141) = 141
        # 707 > 141 → floor doesn't activate here, but child_fee_sats ≥ 141
        min_child_fee = math.ceil(MIN_RELAY_FEE_RATE * ESTIMATED_CHILD_VSIZE)
        assert advice.child_fee_sats >= min_child_fee

    def test_floor_on_very_low_target(self):
        """If target_fee_rate is very low, child fee still ≥ minrelay × child_vsize."""
        advice = evaluate_cpfp(
            parent_fee_sats=50,
            parent_vsize=200.0,
            target_fee_rate=0.5,
        )
        min_child_fee = math.ceil(MIN_RELAY_FEE_RATE * ESTIMATED_CHILD_VSIZE)
        assert advice.child_fee_sats >= min_child_fee


class TestCPFPPackageRate:
    """Package fee rate: (parent_fee + child_fee) / (parent_vsize + child_vsize)."""

    def test_package_rate_reaches_target(self):
        """After CPFP, the package rate must be ≥ target_fee_rate."""
        advice = evaluate_cpfp(
            parent_fee_sats=200,
            parent_vsize=200.0,
            target_fee_rate=5.0,
        )
        assert advice.package_fee_rate >= 5.0 - 0.01  # Allow tiny rounding

    def test_package_rate_computed_correctly(self):
        """Verify package rate formula: (parent + child) / (parent_v + child_v)."""
        advice = evaluate_cpfp(
            parent_fee_sats=200,
            parent_vsize=200.0,
            target_fee_rate=5.0,
        )
        expected_rate = (200 + advice.child_fee_sats) / (200.0 + ESTIMATED_CHILD_VSIZE)
        assert advice.package_fee_rate == pytest.approx(expected_rate)
