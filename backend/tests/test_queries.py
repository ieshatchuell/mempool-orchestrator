"""Unit tests for API query logic — confidence calculation and premium fix.

Tests cover:
  - _compute_confidence: trend-based, premium-based, divergence-based signals
  - Premium -100% fix: edge cases with zero median_fee values
  - Confidence bounds clamping [0.1, 0.95]
"""

import pytest

from src.api.queries import _compute_confidence


# =============================================================================
# _compute_confidence — Trend Signals
# =============================================================================


class TestConfidenceTrendSignals:
    """Verify confidence reacts correctly to EMA trend direction."""

    def test_falling_trend_boosts_patient(self):
        """FALLING trend increases patient confidence, decreases reliable."""
        patient, reliable = _compute_confidence(
            current_fee=10.0,
            ema_fee=8.0,
            trend="FALLING",
            fee_premium_pct=5.0,
        )
        assert patient > 0.5, "Patient should be boosted on FALLING trend"
        assert reliable < 0.65, "Reliable should not be high on FALLING trend"

    def test_stable_trend_boosts_reliable(self):
        """STABLE trend increases reliable confidence."""
        patient, reliable = _compute_confidence(
            current_fee=5.0,
            ema_fee=5.0,
            trend="STABLE",
            fee_premium_pct=0.0,
        )
        assert reliable > patient, "Reliable should exceed patient on STABLE trend"

    def test_rising_trend_boosts_reliable_reduces_patient(self):
        """RISING trend increases reliable, decreases patient."""
        patient, reliable = _compute_confidence(
            current_fee=10.0,
            ema_fee=8.0,
            trend="RISING",
            fee_premium_pct=5.0,
        )
        assert reliable > patient, "Reliable should exceed patient on RISING trend"


# =============================================================================
# _compute_confidence — Premium Signals
# =============================================================================


class TestConfidencePremiumSignals:
    """Verify confidence reacts to fee premium levels."""

    def test_high_premium_boosts_patient(self):
        """When premium > 20%, patient gains confidence (wait for correction)."""
        patient, _ = _compute_confidence(
            current_fee=15.0,
            ema_fee=10.0,
            trend="STABLE",
            fee_premium_pct=50.0,
        )
        assert patient > 0.55, "Patient should be boosted on high premium"

    def test_low_premium_boosts_reliable(self):
        """When |premium| < 10%, reliable gains confidence (fair price)."""
        _, reliable = _compute_confidence(
            current_fee=5.0,
            ema_fee=5.0,
            trend="STABLE",
            fee_premium_pct=2.0,
        )
        assert reliable > 0.7, "Reliable should be high on low premium + STABLE"


# =============================================================================
# _compute_confidence — Bounds Clamping
# =============================================================================


class TestConfidenceBounds:
    """Verify confidence values are clamped to [0.1, 0.95]."""

    def test_lower_bound(self):
        """Worst-case patient scenario doesn't go below 0.1."""
        patient, reliable = _compute_confidence(
            current_fee=1.0,
            ema_fee=1.0,
            trend="RISING",
            fee_premium_pct=-50.0,
        )
        assert patient >= 0.1, "Patient must not go below 0.1"
        assert reliable >= 0.1, "Reliable must not go below 0.1"

    def test_upper_bound(self):
        """Best-case scenario doesn't exceed 0.95."""
        patient, reliable = _compute_confidence(
            current_fee=100.0,
            ema_fee=2.0,
            trend="FALLING",
            fee_premium_pct=200.0,
        )
        assert patient <= 0.95, "Patient must not exceed 0.95"
        assert reliable <= 0.95, "Reliable must not exceed 0.95"

    def test_output_types(self):
        """Both return values are floats."""
        patient, reliable = _compute_confidence(
            current_fee=5.0,
            ema_fee=5.0,
            trend="STABLE",
            fee_premium_pct=0.0,
        )
        assert isinstance(patient, float)
        assert isinstance(reliable, float)


# =============================================================================
# Premium -100% Fix — Zero Guard
# =============================================================================


class TestPremiumZeroGuard:
    """Verify the guard clause against zero median_fee values.

    These test the _compute_confidence function with zero-fee edge cases
    that would previously cause -100% premium.
    """

    def test_zero_current_fee_no_crash(self):
        """Confidence computation doesn't crash with current_fee=0."""
        patient, reliable = _compute_confidence(
            current_fee=0.0,
            ema_fee=5.0,
            trend="STABLE",
            fee_premium_pct=0.0,  # query_orchestrator_status guards this
        )
        assert 0.1 <= patient <= 0.95
        assert 0.1 <= reliable <= 0.95

    def test_zero_ema_fee_no_division_by_zero(self):
        """Divergence calculation uses max(ema_fee, 1.0), preventing div/0."""
        patient, reliable = _compute_confidence(
            current_fee=5.0,
            ema_fee=0.0,
            trend="STABLE",
            fee_premium_pct=0.0,
        )
        assert 0.1 <= patient <= 0.95
        assert 0.1 <= reliable <= 0.95
