"""Unit tests for evaluate_market_rules() — Dual-Mode Strategy Engine.

Tests both PATIENT (20% Premium + EMA confidence) and RELIABLE (EMA-20)
modes, including EMA trend confidence adjustments.
"""

import math

import pytest

from src.orchestrator.schemas import MempoolContext


# Import the function under test
from src.orchestrator.main import evaluate_market_rules


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _ctx(**overrides) -> MempoolContext:
    """Build a MempoolContext with sensible defaults, overridable per test."""
    defaults = dict(
        current_median_fee=5.0,
        historical_median_fee=4.0,
        mempool_size=20_000,
        mempool_bytes=10_000_000,
        fee_premium_pct=25.0,
        traffic_level="NORMAL",
        ema_fee=4.5,
        ema_trend="STABLE",
    )
    defaults.update(overrides)
    return MempoolContext(**defaults)


# =============================================================================
# PATIENT MODE
# =============================================================================

class TestPatientMode:
    """Tests for PATIENT strategy mode (20% Premium + EMA confidence)."""

    def test_wait_on_high_premium(self):
        """Premium > 20% → WAIT, fee = ceil(historical)."""
        ctx = _ctx(
            current_median_fee=10.0,
            historical_median_fee=4.0,
            fee_premium_pct=150.0,
        )
        decision = evaluate_market_rules(ctx)

        assert decision["action"] == "WAIT"
        assert decision["recommended_fee"] == max(1, math.ceil(4.0))
        assert decision["strategy_mode"] == "PATIENT"

    def test_broadcast_on_low_premium(self):
        """Premium <= 20% → BROADCAST, fee = ceil(current)."""
        ctx = _ctx(
            current_median_fee=2.3,
            historical_median_fee=4.0,
            fee_premium_pct=-42.5,
        )
        decision = evaluate_market_rules(ctx)

        assert decision["action"] == "BROADCAST"
        assert decision["recommended_fee"] == max(1, math.ceil(2.3))
        assert decision["strategy_mode"] == "PATIENT"

    def test_broadcast_at_exact_threshold(self):
        """Premium == 20% → BROADCAST (threshold is strictly >20)."""
        ctx = _ctx(fee_premium_pct=20.0)
        decision = evaluate_market_rules(ctx)

        assert decision["action"] == "BROADCAST"

    def test_minrelayfee_floor(self):
        """Both actions enforce max(1, ceil(...)) floor."""
        ctx = _ctx(
            current_median_fee=0.14,
            historical_median_fee=0.1,
            fee_premium_pct=40.0,
        )
        decision = evaluate_market_rules(ctx)

        assert decision["action"] == "WAIT"
        assert decision["recommended_fee"] >= 1

    def test_confidence_high_premium(self):
        """abs(premium) > 30 → base confidence 0.9."""
        ctx = _ctx(fee_premium_pct=50.0)
        decision = evaluate_market_rules(ctx)

        # 0.9 base, +0.1 for RISING would push it further, but we're STABLE
        assert decision["confidence"] == 0.9

    def test_confidence_medium_premium(self):
        """10 < abs(premium) <= 30 → base confidence 0.7."""
        ctx = _ctx(fee_premium_pct=15.0)
        decision = evaluate_market_rules(ctx)

        assert decision["confidence"] == 0.7

    def test_confidence_low_premium(self):
        """abs(premium) <= 10 → base confidence 0.5."""
        ctx = _ctx(fee_premium_pct=5.0)
        decision = evaluate_market_rules(ctx)

        assert decision["confidence"] == 0.5

    # ─── EMA Confidence Adjustments ──────────────────────────────────────

    def test_ema_rising_wait_boosts_confidence(self):
        """WAIT + RISING → confidence +0.1 (fees climbing, WAIT is justified)."""
        ctx = _ctx(fee_premium_pct=50.0, ema_trend="RISING")  # base = 0.9
        decision = evaluate_market_rules(ctx)

        assert decision["action"] == "WAIT"
        assert decision["confidence"] == pytest.approx(1.0)  # 0.9 + 0.1, capped at 1.0

    def test_ema_rising_broadcast_lowers_confidence(self):
        """BROADCAST + RISING → confidence -0.15 (fees climbing, risky to broadcast)."""
        ctx = _ctx(fee_premium_pct=5.0, ema_trend="RISING")  # base = 0.5
        decision = evaluate_market_rules(ctx)

        assert decision["action"] == "BROADCAST"
        assert decision["confidence"] == pytest.approx(0.35)  # 0.5 - 0.15

    def test_ema_falling_wait_lowers_confidence(self):
        """WAIT + FALLING → confidence -0.1 (fees dropping, maybe too cautious)."""
        ctx = _ctx(fee_premium_pct=50.0, ema_trend="FALLING")  # base = 0.9
        decision = evaluate_market_rules(ctx)

        assert decision["action"] == "WAIT"
        assert decision["confidence"] == pytest.approx(0.8)  # 0.9 - 0.1

    def test_ema_falling_broadcast_boosts_confidence(self):
        """BROADCAST + FALLING → confidence +0.1 (fees dropping, good to broadcast)."""
        ctx = _ctx(fee_premium_pct=5.0, ema_trend="FALLING")  # base = 0.5
        decision = evaluate_market_rules(ctx)

        assert decision["action"] == "BROADCAST"
        assert decision["confidence"] == pytest.approx(0.6)  # 0.5 + 0.1

    def test_ema_stable_no_adjustment(self):
        """STABLE trend → no confidence change."""
        ctx = _ctx(fee_premium_pct=15.0, ema_trend="STABLE")  # base = 0.7
        decision = evaluate_market_rules(ctx)

        assert decision["confidence"] == pytest.approx(0.7)

    def test_confidence_never_exceeds_bounds(self):
        """Confidence stays within [0.3, 1.0] after EMA adjustments."""
        # Try to push above 1.0
        ctx_high = _ctx(fee_premium_pct=50.0, ema_trend="RISING")  # 0.9 + 0.1
        assert evaluate_market_rules(ctx_high)["confidence"] <= 1.0

        # Try to push below 0.3
        ctx_low = _ctx(fee_premium_pct=5.0, ema_trend="RISING")  # 0.5 - 0.15 = 0.35
        assert evaluate_market_rules(ctx_low)["confidence"] >= 0.3


# =============================================================================
# RELIABLE MODE
# =============================================================================

class TestReliableMode:
    """Tests for RELIABLE strategy mode (EMA-20, always BROADCAST)."""

    def test_always_broadcast(self):
        """RELIABLE always returns BROADCAST, regardless of premium."""
        ctx = _ctx(fee_premium_pct=200.0)
        decision = evaluate_market_rules(ctx, strategy_mode="RELIABLE")

        assert decision["action"] == "BROADCAST"
        assert decision["strategy_mode"] == "RELIABLE"

    def test_uses_ema_fee(self):
        """RELIABLE uses ceil(ema_fee) as recommended fee."""
        ctx = _ctx(ema_fee=3.7)
        decision = evaluate_market_rules(ctx, strategy_mode="RELIABLE")

        assert decision["recommended_fee"] == max(1, math.ceil(3.7))

    def test_ignores_premium(self):
        """RELIABLE doesn't WAIT even at extreme premiums."""
        ctx = _ctx(
            fee_premium_pct=500.0,
            ema_fee=10.0,
        )
        decision = evaluate_market_rules(ctx, strategy_mode="RELIABLE")

        assert decision["action"] == "BROADCAST"

    def test_fallback_to_current_when_ema_zero(self):
        """RELIABLE falls back to current_median_fee when ema_fee is 0."""
        ctx = _ctx(
            ema_fee=0.0,
            current_median_fee=5.0,
        )
        decision = evaluate_market_rules(ctx, strategy_mode="RELIABLE")

        assert decision["recommended_fee"] == max(1, math.ceil(5.0))

    def test_minrelayfee_floor(self):
        """RELIABLE enforces max(1, ...) floor."""
        ctx = _ctx(ema_fee=0.3)
        decision = evaluate_market_rules(ctx, strategy_mode="RELIABLE")

        assert decision["recommended_fee"] >= 1

    def test_fixed_confidence(self):
        """RELIABLE always returns confidence 0.8."""
        ctx = _ctx()
        decision = evaluate_market_rules(ctx, strategy_mode="RELIABLE")

        assert decision["confidence"] == 0.8

    def test_strategy_mode_in_output(self):
        """strategy_mode field is present in MarketDecision output."""
        for mode in ["PATIENT", "RELIABLE"]:
            ctx = _ctx()
            decision = evaluate_market_rules(ctx, strategy_mode=mode)
            assert decision["strategy_mode"] == mode
