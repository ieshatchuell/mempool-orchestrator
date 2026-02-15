"""Unit tests for strategies.py — Pure fee strategy functions.

Tests naive, SMA, EMA, orchestrator strategies and utility functions.
These are pure functions with no I/O dependencies.
"""

import math

import pytest

from src.strategies import (
    strategy_naive,
    strategy_sma,
    strategy_ema,
    strategy_orchestrator,
    check_hit,
    compute_strategy_fees,
    compute_slippage,
)


class TestNaiveStrategy:
    """S0: Always pay the current block's median fee."""

    def test_returns_ceil(self):
        assert strategy_naive(2.3) == 3.0

    def test_returns_ceil_exact(self):
        assert strategy_naive(5.0) == 5.0

    def test_floor_enforced(self):
        """Never below minrelaytxfee (1 sat/vB)."""
        assert strategy_naive(0.14) == 1.0

    def test_floor_on_zero(self):
        assert strategy_naive(0.0) == 1.0


class TestSMAStrategy:
    """S1: Simple Moving Average of last N blocks."""

    def test_fallback_to_naive(self):
        """Insufficient history → falls back to naive."""
        result = strategy_sma([1.0, 2.0], 5.0, window=20)
        assert result == strategy_naive(5.0)

    def test_full_window(self):
        """With enough history, computes SMA correctly."""
        history = [2.0] * 20
        result = strategy_sma(history, 10.0, window=20)
        # SMA of twenty 2.0s = 2.0 → ceil = 2.0
        assert result == 2.0

    def test_floor_enforced(self):
        history = [0.1] * 20
        result = strategy_sma(history, 0.1, window=20)
        assert result >= 1.0


class TestEMAStrategy:
    """S2: Exponential Moving Average."""

    def test_first_call_uses_raw(self):
        """prev_ema=None → EMA starts at the raw value."""
        fee, ema_state = strategy_ema(None, 5.0)
        assert fee == max(1.0, math.ceil(5.0))
        assert ema_state == 5.0

    def test_smoothing_converges(self):
        """Subsequent calls should converge toward the new value."""
        _, ema = strategy_ema(None, 2.0)
        for _ in range(50):
            _, ema = strategy_ema(ema, 10.0)
        # After 50 steps all at 10.0, EMA should be very close to 10.0
        assert abs(ema - 10.0) < 0.1

    def test_floor_enforced(self):
        fee, _ = strategy_ema(None, 0.1)
        assert fee >= 1.0


class TestOrchestratorStrategy:
    """S3: 20% Premium threshold strategy."""

    def test_wait_on_high_premium(self):
        """Current fee >> historical → recommends historical (lower)."""
        history = [2.0] * 100
        result = strategy_orchestrator(history, 10.0)  # 400% premium
        assert result == max(1, math.ceil(2.0))

    def test_broadcast_on_low_premium(self):
        """Current fee ≈ historical → recommends current."""
        history = [5.0] * 100
        result = strategy_orchestrator(history, 5.5)  # 10% premium
        assert result == max(1, math.ceil(5.5))

    def test_empty_history_fallback(self):
        """No history → falls back to naive."""
        result = strategy_orchestrator([], 5.0)
        assert result == strategy_naive(5.0)

    def test_floor_enforced(self):
        history = [0.1] * 100
        result = strategy_orchestrator(history, 0.05)
        assert result >= 1.0


class TestCheckHit:
    """Would our fee have entered the block?"""

    def test_above_minimum(self):
        assert check_hit(5.0, [1.0, 2.0, 10.0]) is True

    def test_below_minimum(self):
        assert check_hit(0.5, [1.0, 2.0, 10.0]) is False

    def test_equal_to_minimum(self):
        assert check_hit(1.0, [1.0, 2.0, 10.0]) is True

    def test_empty_fee_range(self):
        """Empty fee_range → assume entry (conservative)."""
        assert check_hit(0.1, []) is True


class TestComputeStrategyFees:
    """Integration test for batch strategy computation."""

    def test_naive_cost_matches_sum(self):
        fees = [1.0, 2.0, 3.0, 4.0, 5.0]
        ranges = [[0.5]] * 5
        result = compute_strategy_fees(fees, ranges, "naive")

        expected = sum(max(1.0, math.ceil(f)) for f in fees)
        assert result.cumulative_cost == expected

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            compute_strategy_fees([1.0], [[0.5]], "unknown_strategy")

    def test_all_strategies_run(self):
        """Smoke test: all 4 strategies produce results without errors."""
        fees = [2.0] * 30
        ranges = [[1.0]] * 30
        for name in ("naive", "sma", "ema", "orchestrator"):
            result = compute_strategy_fees(fees, ranges, name)
            assert result.n_blocks == 30
            assert result.cumulative_cost > 0


class TestComputeSlippage:
    """Slippage calculation: (strategy - naive) / naive * 100."""

    def test_savings(self):
        """Strategy costs less → negative slippage (savings)."""
        assert compute_slippage(75.0, 100.0) == pytest.approx(-25.0)

    def test_overpay(self):
        """Strategy costs more → positive slippage."""
        assert compute_slippage(120.0, 100.0) == pytest.approx(20.0)

    def test_zero_baseline(self):
        """Zero naive cost → returns 0.0 (no division by zero)."""
        assert compute_slippage(50.0, 0.0) == 0.0

    def test_equal_cost(self):
        """Same cost → 0% slippage."""
        assert compute_slippage(100.0, 100.0) == pytest.approx(0.0)
