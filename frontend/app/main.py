import json
import os
import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Ensure backend/src is importable for strategies module
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from src.strategies import compute_slippage, compute_strategy_fees
from src.strategies.advisors import evaluate_rbf, evaluate_cpfp, ESTIMATED_CHILD_VSIZE

# Load environment variables from root .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

# Configuration via environment variables (fully decoupled from backend)
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "../data/market/mempool_data.duckdb")
AGENT_HISTORY_PATH = os.getenv("AGENT_HISTORY_PATH", "../data/history/agent_history.duckdb")
STRATEGY_MODE = os.getenv("STRATEGY_MODE", "PATIENT")


# --- DATABASE HELPERS ---

def get_connection() -> duckdb.DuckDBPyConnection:
    """Open a read-only connection to the market DuckDB."""
    db_path = str(Path(DUCKDB_PATH).resolve())
    return duckdb.connect(db_path, read_only=True)


def safe_query(query: str, conn: duckdb.DuckDBPyConnection):
    """Execute a query and return the result, or None on error."""
    try:
        return conn.execute(query).fetchone()
    except Exception:
        return None


def safe_query_df(query: str, conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Execute a query and return a DataFrame, or empty DataFrame on error."""
    try:
        return conn.execute(query).fetchdf()
    except Exception:
        return pd.DataFrame()


# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Mempool Orchestrator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS: Cypherpunk Dark Theme
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #00FF41;
        font-family: 'Courier New', Courier, monospace;
    }
    [data-testid="stMetricValue"] {
        color: #F7931A !important; /* Bitcoin Orange */
        font-family: 'Courier New', Courier, monospace;
    }
    .stDataFrame {
        border: 1px solid #333;
    }
    </style>
    """, unsafe_allow_html=True)


# --- DATA FETCH ---
try:
    conn = get_connection()

    # Latest mempool snapshot
    stats = safe_query("""
        SELECT size, bytes, total_fee
        FROM mempool_stats
        ORDER BY ingestion_time DESC LIMIT 1
    """, conn)

    # Current median fee from mempool_stream (next block projection)
    fee = safe_query("""
        SELECT median_fee
        FROM mempool_stream
        WHERE block_index = 0
        ORDER BY ingestion_time DESC LIMIT 1
    """, conn)

    # Blocks to clear (distinct block indices in latest mempool snapshot)
    blocks_to_clear = safe_query("""
        SELECT COUNT(DISTINCT block_index)
        FROM mempool_stream
        WHERE ingestion_time = (SELECT MAX(ingestion_time) FROM mempool_stream)
    """, conn)

    # Recent blocks table from mempool_stream (block_index=0, last 10)
    blocks_df = safe_query_df("""
        SELECT
            ingestion_time AS "Timestamp",
            n_tx AS "TXs",
            block_size AS "Block Size",
            total_fees AS "Total Fees (sats)",
            ROUND(median_fee, 2) AS "Median Fee (sat/vB)",
            fee_range AS "Fee Range"
        FROM mempool_stream
        WHERE block_index = 0
        ORDER BY ingestion_time DESC
        LIMIT 10
    """, conn)

    # Fee trend from block_history (confirmed blocks, stable trend)
    trend_df = safe_query_df("""
        SELECT
            ingestion_time AS time,
            median_fee AS "Median Fee"
        FROM block_history
        ORDER BY height ASC
    """, conn)

    # Full block_history for Strategy Simulator
    sim_df = safe_query_df("""
        SELECT
            height,
            median_fee,
            fee_range
        FROM block_history
        ORDER BY height ASC
    """, conn)

    conn.close()
    data_available = True

except Exception as e:
    st.error(f"⚠️ Database connection failed: {e}")
    data_available = False


# --- HEADER ---
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    st.title("⚡ MEMPOOL ORCHESTRATOR_")
    st.caption("Real-time Auditor // Hybrid Signal Architecture")
with col2:
    mode_icon = "🐢" if STRATEGY_MODE == "PATIENT" else "⚡"
    mode_color = "#00FF41" if STRATEGY_MODE == "PATIENT" else "#F7931A"
    st.markdown(
        f"### {mode_icon} {STRATEGY_MODE}",
        help="PATIENT: Treasury ops (-27.7%, 82% hit) · RELIABLE: Time-sensitive (-4.9%, 94% hit)"
    )
with col3:
    st.markdown("### 🟢 LIVE" if data_available else "### 🔴 OFFLINE")

# Dust Watch indicator
if data_available and not trend_df.empty:
    latest_fee = trend_df["Median Fee"].iloc[-1] if len(trend_df) > 0 else None
    if latest_fee is not None and latest_fee < 5.0:
        st.success(f"💎 **Dust Watch: Consolidation Window!** Median fee {latest_fee:.2f} sat/vB < 5 sat/vB — ideal for UTXO cleanup.")

# Fee Advisors (RBF/CPFP) — always visible when watchlist has entries
try:
    history_db_path = str(Path(AGENT_HISTORY_PATH).resolve())
    if Path(history_db_path).exists():
        hist_conn = duckdb.connect(history_db_path, read_only=True)
        pending_txs = hist_conn.execute("""
            SELECT txid, role, fee, fee_rate
            FROM watchlist
            WHERE status = 'PENDING'
            ORDER BY added_at ASC
        """).fetchall()
        hist_conn.close()

        if pending_txs:
            st.subheader(f"📡 FEE ADVISORS — {len(pending_txs)} Tracked Transaction(s)")

            current_fee_rate = fee[0] if (data_available and fee) else 1.0
            advisor_alerts = []
            rows = []

            for txid, role, tx_fee, tx_fee_rate in pending_txs:
                row = {
                    "TXID": f"{txid[:16]}...",
                    "Role": f"{'🔄 SENDER' if role == 'SENDER' else '⚡ RECEIVER'}",
                    "Fee Rate": f"{tx_fee_rate:.1f} sat/vB" if tx_fee_rate else "—",
                    "Fee": f"{tx_fee:,} sats" if tx_fee else "—",
                    "Status": "✅ OK",
                    "Advisory": "—",
                }

                if tx_fee is None or tx_fee_rate is None or tx_fee_rate <= 0:
                    row["Status"] = "⏳ Awaiting data"
                    rows.append(row)
                    continue

                vsize = tx_fee / tx_fee_rate if tx_fee_rate > 0 else 0
                if vsize <= 0:
                    rows.append(row)
                    continue

                if role == "SENDER":
                    advice = evaluate_rbf(
                        original_fee_sats=tx_fee,
                        original_fee_rate=tx_fee_rate,
                        original_vsize=vsize,
                        target_fee_rate=current_fee_rate,
                    )
                    if advice.is_stuck:
                        row["Status"] = "🔴 STUCK"
                        row["Advisory"] = (
                            f"RBF → {advice.target_fee_rate:.1f} sat/vB "
                            f"({advice.target_fee_sats:,} sats)"
                        )
                        advisor_alerts.append(
                            f"🔄 **RBF** `{txid[:16]}...` stuck at "
                            f"{advice.original_fee_rate:.1f} sat/vB → "
                            f"recommend **{advice.target_fee_rate:.1f} sat/vB** "
                            f"({advice.target_fee_sats:,} sats)"
                        )
                elif role == "RECEIVER":
                    advice = evaluate_cpfp(
                        parent_fee_sats=tx_fee,
                        parent_vsize=vsize,
                        target_fee_rate=current_fee_rate,
                    )
                    if advice.is_stuck:
                        row["Status"] = "🔴 STUCK"
                        row["Advisory"] = (
                            f"CPFP child: {advice.child_fee_sats:,} sats "
                            f"(pkg: {advice.package_fee_rate:.1f} sat/vB)"
                        )
                        advisor_alerts.append(
                            f"⚡ **CPFP** `{txid[:16]}...` parent stuck at "
                            f"{advice.parent_fee_rate:.1f} sat/vB → "
                            f"child fee: **{advice.child_fee_sats:,} sats** "
                            f"(package: {advice.package_fee_rate:.1f} sat/vB)"
                        )

                rows.append(row)

            # Show alerts if any txs are stuck
            if advisor_alerts:
                st.warning("⚠️ **Stuck transactions detected:**")
                for alert in advisor_alerts:
                    st.markdown(f"  {alert}")
            else:
                st.success(f"✅ All {len(pending_txs)} tracked tx(s) are confirming normally (market: {current_fee_rate:.2f} sat/vB)")

            # Always show the watchlist table
            st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                use_container_width=True,
            )

except Exception:
    pass  # Non-critical: dashboard continues without advisor panel

st.divider()


# --- ROW 1: KPIs ---
if data_available and stats:
    mempool_size = stats[0]
    mempool_bytes = stats[1]
    total_fee_sats = stats[2]
    current_fee = fee[0] if fee else 0
    n_blocks = blocks_to_clear[0] if blocks_to_clear else 0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(
        label="MEMPOOL SIZE (txs)",
        value=f"{mempool_size:,}",
    )
    kpi2.metric(
        label="MEDIAN FEE (sat/vB)",
        value=f"{current_fee:.2f}",
    )
    kpi3.metric(
        label="PENDING FEES (BTC)",
        value=f"{total_fee_sats / 1e8:.4f}",
    )
    kpi4.metric(
        label="BLOCKS TO CLEAR",
        value=f"{n_blocks}",
    )
else:
    st.warning("No mempool data available. Start the pipeline with `just radar` + `just storage`.")


# --- ROW 2: RECENT BLOCKS ---
st.subheader("🧊 RECENT BLOCKS (Next Block Projections)")

if data_available and not blocks_df.empty:
    # Format columns for display
    display_df = blocks_df.copy()
    display_df["Total Fees (sats)"] = display_df["Total Fees (sats)"].apply(lambda x: f"{x:,}")
    display_df["Block Size"] = display_df["Block Size"].apply(lambda x: f"{x:,}")
    display_df["TXs"] = display_df["TXs"].apply(lambda x: f"{x:,}")
    display_df = display_df.drop(columns=["Fee Range"])  # Too wide for display

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True
    )
else:
    st.info("No projected block data yet.")


# --- ROW 3: FEE TREND CHART ---
st.subheader("📈 FEE TREND — Confirmed Block Fees (sat/vB)")

if data_available and not trend_df.empty:
    st.line_chart(
        trend_df.set_index("time"),
        color=["#F7931A"],  # Bitcoin Orange
    )
else:
    st.info("Not enough data for trend chart.")


# --- ROW 4: STRATEGY SIMULATOR ---
st.divider()
st.subheader("📊 STRATEGY SIMULATOR")
st.caption("Compare fee strategies against confirmed block history")

if data_available and not sim_df.empty and len(sim_df) > 1:

    # Parse fee_ranges
    median_fees = sim_df["median_fee"].tolist()
    heights = sim_df["height"].tolist()
    fee_ranges = []
    for fr_raw in sim_df["fee_range"]:
        if isinstance(fr_raw, str):
            try:
                fee_ranges.append(json.loads(fr_raw))
            except (json.JSONDecodeError, TypeError):
                fee_ranges.append([])
        elif isinstance(fr_raw, list):
            fee_ranges.append(fr_raw)
        else:
            fee_ranges.append([])

    # Strategy selector
    strategy_options = {
        "SMA-20 (Simple Moving Average)": "sma",
        "EMA-20 (Exponential Moving Average)": "ema",
        "Orchestrator (20% Premium)": "orchestrator",
    }
    selected_label = st.selectbox(
        "Select Strategy",
        options=list(strategy_options.keys()),
        index=2,  # Default: Orchestrator
    )
    selected_key = strategy_options[selected_label]

    # Run strategies
    naive_result = compute_strategy_fees(median_fees, fee_ranges, "naive")
    strategy_result = compute_strategy_fees(median_fees, fee_ranges, selected_key)
    slippage = compute_slippage(strategy_result.cumulative_cost, naive_result.cumulative_cost)

    # KPIs
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    kpi_col1.metric(
        label="Σ CUMULATIVE COST",
        value=f"{strategy_result.cumulative_cost:.0f} sat/vB",
        delta=f"{slippage:+.1f}% vs market",
        delta_color="inverse",  # negative = green (savings)
    )
    kpi_col2.metric(
        label="SLIPPAGE",
        value=f"{slippage:+.1f}%",
        delta="savings" if slippage < 0 else "overpay",
        delta_color="inverse",
    )
    kpi_col3.metric(
        label="HIT RATE",
        value=f"{strategy_result.hit_rate:.1f}%",
        delta=f"{strategy_result.hit_rate - naive_result.hit_rate:+.1f}% vs naive",
        delta_color="normal",
    )

    # Overlay chart: Truth vs Strategy
    chart_df = pd.DataFrame({
        "height": heights,
        "The Truth (Median Fee)": [max(1.0, f) for f in median_fees],
        f"{strategy_result.name}": strategy_result.fees,
    }).set_index("height")

    st.line_chart(
        chart_df,
        color=["#F7931A", "#00FF41"],  # Orange = truth, Green = strategy
    )

    st.caption(
        f"📦 {len(median_fees)} confirmed blocks "
        f"(heights {heights[0]:,} → {heights[-1]:,}) · "
        f"Naive baseline: {naive_result.cumulative_cost:.0f} sat/vB"
    )

else:
    st.info("Not enough confirmed block data for simulation. Run `uv run python scripts/backfill_history.py` first.")