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
import sys
from pathlib import Path

import duckdb

# Ensure backend/src is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from src.strategies import (
    compute_slippage,
    compute_strategy_fees,
)

# ─── Configuration ───────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "data" / "market" / "mempool_data.duckdb"


# ─── Data Loading ────────────────────────────────────────────────────────────

def load_blocks() -> tuple[list[int], list[float], list[list[float]], list[str | None]]:
    """Load confirmed blocks from DuckDB, ordered by height ASC.

    Returns:
        Tuple of (heights, median_fees, fee_ranges, pool_names).
    """
    db_path = str(DB_PATH.resolve())
    conn = duckdb.connect(db_path, read_only=True)

    try:
        rows = conn.execute("""
            SELECT height, median_fee, fee_range, pool_name
            FROM block_history
            ORDER BY height ASC
        """).fetchall()

        heights: list[int] = []
        median_fees: list[float] = []
        fee_ranges: list[list[float]] = []
        pool_names: list[str | None] = []

        for row in rows:
            height, median_fee, fee_range_raw, pool_name = row

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

            heights.append(height)
            median_fees.append(median_fee)
            fee_ranges.append(fee_range)
            pool_names.append(pool_name)

        return heights, median_fees, fee_ranges, pool_names
    finally:
        conn.close()


# ─── Report ──────────────────────────────────────────────────────────────────

def print_report(
    n_blocks: int,
    heights: list[int],
    median_fees: list[float],
    results: dict[str, object],
) -> None:
    """Print formatted comparison report."""
    naive_cost = results["naive"].cumulative_cost

    # Header
    print()
    print("╔" + "═" * 62 + "╗")
    print(f"║{'SCIENTIFIC BACKTEST — ' + str(n_blocks) + ' Blocks':^62}║")
    print("╠" + "═" * 62 + "╣")
    print(f"║ {'Strategy':<22}│ {'Σ Cost':>10} │ {'Slippage':>9} │ {'Hit Rate':>9} ║")
    print("║" + "─" * 22 + "┼" + "─" * 12 + "┼" + "─" * 11 + "┼" + "─" * 11 + "║")

    # Rows
    for key in ["naive", "sma", "ema", "orchestrator"]:
        r = results[key]
        cost = r.cumulative_cost
        slippage = compute_slippage(cost, naive_cost)
        slippage_str = f"{slippage:+.1f}%" if key != "naive" else "baseline"

        print(f"║ {r.name:<22}│ {cost:>8.0f} sv │ {slippage_str:>9} │ {r.hit_rate:>8.1f}% ║")

    print("╠" + "═" * 62 + "╣")

    # Summary
    orch = results["orchestrator"]
    orch_slippage = compute_slippage(orch.cumulative_cost, naive_cost)
    if orch_slippage < 0:
        msg = f"✅ Orchestrator saves {abs(orch_slippage):.1f}% vs market. Hit rate: {orch.hit_rate:.0f}%"
    else:
        msg = f"⚠️  Orchestrator overpays {orch_slippage:.1f}% vs market. Hit rate: {orch.hit_rate:.0f}%"
    print(f"║ {msg:<62}║")

    # Find best
    best_key = min(results, key=lambda k: results[k].cumulative_cost)
    best = results[best_key]
    if best_key != "orchestrator":
        best_slip = compute_slippage(best.cumulative_cost, naive_cost)
        best_msg = f"💡 Best: {best.name} ({best_slip:+.1f}%)"
        print(f"║ {best_msg:<62}║")

    print("╚" + "═" * 62 + "╝")

    # Block stats
    import statistics
    print(f"\n📊 Block Stats:")
    print(f"   Height range: {heights[0]} → {heights[-1]}")
    print(f"   Median fee range: {min(median_fees):.2f} – {max(median_fees):.2f} sat/vB")
    print(f"   Avg median fee: {statistics.mean(median_fees):.2f} sat/vB")
    zero_fee = sum(1 for f in median_fees if f == 0)
    print(f"   Zero-fee blocks: {zero_fee}/{len(median_fees)} ({zero_fee/len(median_fees)*100:.0f}%)")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("🔬 Scientific Backtesting Engine")
    print(f"   Database: {DB_PATH.resolve()}")
    print()

    heights, median_fees, fee_ranges, _ = load_blocks()
    if len(median_fees) < 2:
        print("❌ Not enough blocks in block_history. Run backfill first.")
        return

    print(f"📦 Loaded {len(median_fees)} confirmed blocks from block_history")

    # Run all 4 strategies via the shared module
    results = {}
    for name in ["naive", "sma", "ema", "orchestrator"]:
        results[name] = compute_strategy_fees(median_fees, fee_ranges, name)

    # Sanity check: S0 cost should equal sum of ceil'd median fees
    expected_naive = sum(max(1.0, math.ceil(f)) for f in median_fees)
    actual_naive = results["naive"].cumulative_cost
    assert actual_naive == expected_naive, f"Sanity check failed: {actual_naive} != {expected_naive}"

    print_report(len(median_fees), heights, median_fees, results)


if __name__ == "__main__":
    main()
