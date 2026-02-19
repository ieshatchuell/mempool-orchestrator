"""Reusable fee strategy functions for backtesting and simulation.

Each strategy takes historical block data and returns a recommended fee (sat/vB).
All strategies apply: ceil() for safety + max(1.0, ...) for minrelaytxfee floor.

Strategies:
    - naive:        Always pay the current block's median fee.
    - sma:          Simple Moving Average of last N blocks.
    - ema:          Exponential Moving Average (stateful).
    - orchestrator: 20% Premium threshold (mirrors evaluate_market_rules).
"""

import math
import statistics
from dataclasses import dataclass, field


# ─── Constants ───────────────────────────────────────────────────────────────

SMA_WINDOW = 20
EMA_WINDOW = 20
ORCHESTRATOR_WINDOW = 100
PREMIUM_THRESHOLD = 20.0  # percent


# ─── Data Structures ────────────────────────────────────────────────────────

@dataclass
class StrategyResult:
    """Accumulated results for a single strategy."""

    name: str
    fees: list[float] = field(default_factory=list)
    hits: list[bool] = field(default_factory=list)

    @property
    def cumulative_cost(self) -> float:
        return sum(self.fees)

    @property
    def hit_rate(self) -> float:
        if not self.hits:
            return 0.0
        return sum(1 for h in self.hits if h) / len(self.hits) * 100

    @property
    def slippage(self) -> float | None:
        """Slippage vs naive (requires external naive_cost)."""
        return None  # Computed externally

    @property
    def n_blocks(self) -> int:
        return len(self.fees)


# ─── Strategy Functions ─────────────────────────────────────────────────────

def strategy_naive(median_fee: float) -> float:
    """S0: Always pay the current block's median fee.

    Args:
        median_fee: Current block's median fee in sat/vB.

    Returns:
        Recommended fee in sat/vB (always >= 1.0).
    """
    return max(1.0, math.ceil(median_fee))


def strategy_sma(
    history_fees: list[float],
    current_fee: float,
    window: int = SMA_WINDOW,
) -> float:
    """S1: Pay the Simple Moving Average of last N blocks.

    Falls back to naive if insufficient history.

    Args:
        history_fees: List of median_fee values from previous blocks.
        current_fee: Current block's median fee.
        window: Number of blocks to average.

    Returns:
        Recommended fee in sat/vB.
    """
    if len(history_fees) < window:
        return strategy_naive(current_fee)
    recent = history_fees[-window:]
    return max(1.0, math.ceil(statistics.mean(recent)))


def strategy_ema(
    prev_ema: float | None,
    median_fee: float,
    window: int = EMA_WINDOW,
) -> tuple[float, float]:
    """S2: Pay the Exponential Moving Average.

    EMA reacts faster to recent changes than SMA.

    Args:
        prev_ema: Previous EMA value (None on first call).
        median_fee: Current block's median fee.
        window: Smoothing window (α = 2/(window+1)).

    Returns:
        Tuple of (recommended_fee, new_ema_state).
    """
    alpha = 2.0 / (window + 1)
    if prev_ema is None:
        ema = median_fee
    else:
        ema = alpha * median_fee + (1 - alpha) * prev_ema
    return max(1.0, math.ceil(ema)), ema


def strategy_orchestrator(
    history_fees: list[float],
    current_fee: float,
    window: int = ORCHESTRATOR_WINDOW,
    threshold: float = PREMIUM_THRESHOLD,
) -> float:
    """S3: Replay our 20% Premium strategy.

    Mirrors evaluate_market_rules() in main.py exactly:
    - Compute historical median over last N confirmed blocks
    - If current fee > 1.2× historical → WAIT (pay historical)
    - Else → BROADCAST (pay current)
    - Always ceil() + max(1, ...)

    Args:
        history_fees: List of median_fee values from previous blocks.
        current_fee: Current block's median fee.
        window: Lookback window for historical median.
        threshold: Premium percentage threshold to trigger WAIT.

    Returns:
        Recommended fee in sat/vB.
    """
    if not history_fees:
        return strategy_naive(current_fee)

    lookback = history_fees[-window:] if len(history_fees) >= window else history_fees
    historical_median = max(1.0, statistics.median(lookback))

    if historical_median > 0:
        premium = ((current_fee - historical_median) / historical_median) * 100
    else:
        premium = 0.0

    if premium > threshold:
        # WAIT — pay historical baseline
        return max(1, math.ceil(historical_median))
    else:
        # BROADCAST — pay current market
        return max(1, math.ceil(current_fee))


def check_hit(recommended_fee: float, fee_range: list[float]) -> bool:
    """Would our recommended fee have entered this block?

    Approximation: fee >= lowest fee in the block's fee_range.
    If fee_range is empty, assume entry (conservative).

    Args:
        recommended_fee: The strategy's recommended fee.
        fee_range: The block's fee_range list from block_history.

    Returns:
        True if the transaction would have been included.
    """
    if not fee_range:
        return True
    return recommended_fee >= fee_range[0]


# ─── Batch Compute ──────────────────────────────────────────────────────────

def compute_strategy_fees(
    median_fees: list[float],
    fee_ranges: list[list[float]],
    strategy_name: str,
) -> StrategyResult:
    """Run a single strategy over all blocks and return results.

    This is the main entry point for both backtest.py and the dashboard.

    Args:
        median_fees: Ordered list of median_fee per block (by height ASC).
        fee_ranges: Ordered list of fee_range per block.
        strategy_name: One of 'naive', 'sma', 'ema', 'orchestrator'.

    Returns:
        StrategyResult with fees and hits populated.
    """
    display_names = {
        "naive": "S0 Naive (Market)",
        "sma": f"S1 SMA-{SMA_WINDOW}",
        "ema": f"S2 EMA-{EMA_WINDOW}",
        "orchestrator": "S3 Orchestrator",
    }

    result = StrategyResult(name=display_names.get(strategy_name, strategy_name))
    ema_state: float | None = None

    for i, median_fee in enumerate(median_fees):
        history = median_fees[:i]
        fr = fee_ranges[i] if i < len(fee_ranges) else []

        if strategy_name == "naive":
            fee = strategy_naive(median_fee)
        elif strategy_name == "sma":
            fee = strategy_sma(history, median_fee)
        elif strategy_name == "ema":
            fee, ema_state = strategy_ema(ema_state, median_fee)
        elif strategy_name == "orchestrator":
            fee = strategy_orchestrator(history, median_fee)
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        result.fees.append(fee)
        result.hits.append(check_hit(fee, fr))

    return result


def compute_slippage(strategy_cost: float, naive_cost: float) -> float:
    """Compute slippage percentage vs naive baseline.

    Args:
        strategy_cost: Cumulative cost of the strategy.
        naive_cost: Cumulative cost of the naive (market pay) strategy.

    Returns:
        Slippage as percentage (negative = savings).
    """
    if naive_cost == 0:
        return 0.0
    return ((strategy_cost - naive_cost) / naive_cost) * 100
