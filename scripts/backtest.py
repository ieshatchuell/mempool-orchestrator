#!/usr/bin/env python3
"""Scientific Backtesting — Fee Strategy Comparison.

Replays 4 fee strategies against confirmed block history to measure:
- Cumulative cost (Σ sat/vB)
- Slippage vs market (% overpaid)
- Hit rate (% of blocks where our fee would enter)

Usage:
    cd backend && uv run python ../scripts/backtest.py
"""

import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path

import duckdb


# ─── Configuration ───────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "data" / "market" / "mempool_data.duckdb"
SMA_WINDOW = 20
EMA_WINDOW = 20
ORCHESTRATOR_WINDOW = 100
PREMIUM_THRESHOLD = 20.0  # percent


# ─── Data Structures ────────────────────────────────────────────────────────

@dataclass
class Block:
    """Confirmed block from block_history."""
    height: int
    median_fee: float
    fee_range: list[float]
    total_fees: int
    n_tx: int
    pool_name: str | None


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
    def n_blocks(self) -> int:
        return len(self.fees)


# ─── Strategy Functions ─────────────────────────────────────────────────────

def strategy_naive(block: Block) -> float:
    """S0: Always pay the current block's median fee."""
    return max(1.0, math.ceil(block.median_fee))


def strategy_sma(history: list[Block], current: Block, window: int = SMA_WINDOW) -> float:
    """S1: Pay the Simple Moving Average of last N blocks."""
    if len(history) < window:
        return strategy_naive(current)
    recent = [b.median_fee for b in history[-window:]]
    return max(1.0, math.ceil(statistics.mean(recent)))


def strategy_ema(prev_ema: float | None, current: Block, window: int = EMA_WINDOW) -> tuple[float, float]:
    """S2: Pay the Exponential Moving Average.
    
    Returns (recommended_fee, new_ema) for state tracking.
    """
    alpha = 2.0 / (window + 1)
    if prev_ema is None:
        ema = current.median_fee
    else:
        ema = alpha * current.median_fee + (1 - alpha) * prev_ema
    return max(1.0, math.ceil(ema)), ema


def strategy_orchestrator(history: list[Block], current: Block, window: int = ORCHESTRATOR_WINDOW) -> float:
    """S3: Replay our 20% Premium strategy exactly.
    
    Logic mirrors evaluate_market_rules() in main.py:
    - Compute historical median over last N confirmed blocks
    - If current fee > 1.2× historical → WAIT (pay historical)
    - Else → BROADCAST (pay current)
    - Always ceil() + max(1, ...)
    """
    if len(history) < 1:
        return strategy_naive(current)

    lookback = history[-window:] if len(history) >= window else history
    historical_median = max(1.0, statistics.median([b.median_fee for b in lookback]))

    current_fee = current.median_fee
    if historical_median > 0:
        premium = ((current_fee - historical_median) / historical_median) * 100
    else:
        premium = 0.0

    if premium > PREMIUM_THRESHOLD:
        # WAIT — pay historical baseline
        return max(1, math.ceil(historical_median))
    else:
        # BROADCAST — pay current market
        return max(1, math.ceil(current_fee))


def check_hit(recommended_fee: float, block: Block) -> bool:
    """Would our recommended fee have entered this block?
    
    Approximation: fee >= lowest fee in the block's fee_range.
    If fee_range is empty, assume entry (conservative).
    """
    if not block.fee_range:
        return True
    min_fee_to_enter = block.fee_range[0]
    return recommended_fee >= min_fee_to_enter


# ─── Data Loading ────────────────────────────────────────────────────────────

def load_blocks() -> list[Block]:
    """Load confirmed blocks from DuckDB, ordered by height ASC."""
    db_path = str(DB_PATH.resolve())
    conn = duckdb.connect(db_path, read_only=True)

    try:
        rows = conn.execute("""
            SELECT height, median_fee, fee_range, total_fees, n_tx, pool_name
            FROM block_history
            ORDER BY height ASC
        """).fetchall()

        blocks = []
        for row in rows:
            height, median_fee, fee_range_raw, total_fees, n_tx, pool_name = row

            # Parse fee_range from JSON string or list
            if isinstance(fee_range_raw, str):
                try:
                    fee_range = json.loads(fee_range_raw)
                except (json.JSONDecodeError, TypeError):
                    fee_range = []
            elif isinstance(fee_range_raw, list):
                fee_range = fee_range_raw
            else:
                fee_range = []

            blocks.append(Block(
                height=height,
                median_fee=median_fee,
                fee_range=fee_range,
                total_fees=total_fees,
                n_tx=n_tx,
                pool_name=pool_name,
            ))

        return blocks
    finally:
        conn.close()


# ─── Backtest Engine ─────────────────────────────────────────────────────────

def run_backtest(blocks: list[Block]) -> dict[str, StrategyResult]:
    """Run all 4 strategies against block history."""
    results = {
        "S0_Naive": StrategyResult(name="S0 Naive (Market)"),
        "S1_SMA": StrategyResult(name=f"S1 SMA-{SMA_WINDOW}"),
        "S2_EMA": StrategyResult(name=f"S2 EMA-{EMA_WINDOW}"),
        "S3_Orch": StrategyResult(name="S3 Orchestrator"),
    }

    ema_state: float | None = None  # EMA running state

    for i, block in enumerate(blocks):
        history = blocks[:i]  # All blocks before this one

        # S0: Naive
        s0_fee = strategy_naive(block)
        results["S0_Naive"].fees.append(s0_fee)
        results["S0_Naive"].hits.append(check_hit(s0_fee, block))

        # S1: SMA
        s1_fee = strategy_sma(history, block)
        results["S1_SMA"].fees.append(s1_fee)
        results["S1_SMA"].hits.append(check_hit(s1_fee, block))

        # S2: EMA
        s2_fee, ema_state = strategy_ema(ema_state, block)
        results["S2_EMA"].fees.append(s2_fee)
        results["S2_EMA"].hits.append(check_hit(s2_fee, block))

        # S3: Orchestrator
        s3_fee = strategy_orchestrator(history, block)
        results["S3_Orch"].fees.append(s3_fee)
        results["S3_Orch"].hits.append(check_hit(s3_fee, block))

    return results


# ─── Report ──────────────────────────────────────────────────────────────────

def print_report(blocks: list[Block], results: dict[str, StrategyResult]) -> None:
    """Print formatted comparison report."""
    naive_cost = results["S0_Naive"].cumulative_cost

    # Header
    print()
    print("╔" + "═" * 62 + "╗")
    print(f"║{'SCIENTIFIC BACKTEST — ' + str(len(blocks)) + ' Blocks':^62}║")
    print("╠" + "═" * 62 + "╣")
    print(f"║ {'Strategy':<22}│ {'Σ Cost':>10} │ {'Slippage':>9} │ {'Hit Rate':>9} ║")
    print("║" + "─" * 22 + "┼" + "─" * 12 + "┼" + "─" * 11 + "┼" + "─" * 11 + "║")

    # Rows
    for key in ["S0_Naive", "S1_SMA", "S2_EMA", "S3_Orch"]:
        r = results[key]
        cost = r.cumulative_cost
        if naive_cost > 0:
            slippage = ((cost - naive_cost) / naive_cost) * 100
        else:
            slippage = 0.0
        slippage_str = f"{slippage:+.1f}%"
        if key == "S0_Naive":
            slippage_str = "baseline"

        print(f"║ {r.name:<22}│ {cost:>8.0f} sv │ {slippage_str:>9} │ {r.hit_rate:>8.1f}% ║")

    print("╠" + "═" * 62 + "╣")

    # Summary
    orch = results["S3_Orch"]
    orch_slippage = ((orch.cumulative_cost - naive_cost) / naive_cost) * 100 if naive_cost > 0 else 0
    if orch_slippage < 0:
        print(f"║ ✅ Orchestrator saves {abs(orch_slippage):.1f}% vs market. Hit rate: {orch.hit_rate:.0f}%{' ' * (62 - 54 - len(f'{abs(orch_slippage):.1f}') - len(f'{orch.hit_rate:.0f}'))}║")
    else:
        print(f"║ ⚠️  Orchestrator overpays {orch_slippage:.1f}% vs market. Hit rate: {orch.hit_rate:.0f}%{' ' * max(1, 62 - 57 - len(f'{orch_slippage:.1f}') - len(f'{orch.hit_rate:.0f}'))}║")

    # Find best strategy
    best_key = min(results, key=lambda k: results[k].cumulative_cost)
    best = results[best_key]
    if best_key != "S3_Orch":
        best_slip = ((best.cumulative_cost - naive_cost) / naive_cost) * 100 if naive_cost > 0 else 0
        print(f"║ 💡 Best: {best.name} ({best_slip:+.1f}%){' ' * max(1, 62 - 16 - len(best.name) - len(f'{best_slip:+.1f}'))}║")

    print("╚" + "═" * 62 + "╝")

    # Block stats
    median_fees = [b.median_fee for b in blocks]
    print(f"\n📊 Block Stats:")
    print(f"   Height range: {blocks[0].height} → {blocks[-1].height}")
    print(f"   Median fee range: {min(median_fees):.2f} – {max(median_fees):.2f} sat/vB")
    print(f"   Avg median fee: {statistics.mean(median_fees):.2f} sat/vB")
    zero_fee = sum(1 for b in blocks if b.median_fee == 0)
    print(f"   Zero-fee blocks: {zero_fee}/{len(blocks)} ({zero_fee/len(blocks)*100:.0f}%)")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("🔬 Scientific Backtesting Engine")
    print(f"   Database: {DB_PATH.resolve()}")
    print(f"   Strategies: Naive, SMA-{SMA_WINDOW}, EMA-{EMA_WINDOW}, Orchestrator (>{PREMIUM_THRESHOLD}% threshold)")
    print()

    blocks = load_blocks()
    if len(blocks) < 2:
        print("❌ Not enough blocks in block_history. Run backfill first.")
        return

    print(f"📦 Loaded {len(blocks)} confirmed blocks from block_history")

    results = run_backtest(blocks)

    # Sanity check: S0 cost should equal sum of ceil'd median fees
    expected_naive = sum(max(1.0, math.ceil(b.median_fee)) for b in blocks)
    actual_naive = results["S0_Naive"].cumulative_cost
    assert actual_naive == expected_naive, f"Sanity check failed: {actual_naive} != {expected_naive}"

    print_report(blocks, results)


if __name__ == "__main__":
    main()
