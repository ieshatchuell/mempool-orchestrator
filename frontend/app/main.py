import os
import streamlit as st
import pandas as pd
import duckdb
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from root .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

# Configuration via environment variables (fully decoupled from backend)
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "../data/market/mempool_data.duckdb")


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

    conn.close()
    data_available = True

except Exception as e:
    st.error(f"⚠️ Database connection failed: {e}")
    data_available = False


# --- HEADER ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("⚡ MEMPOOL ORCHESTRATOR_")
    st.caption("Real-time Auditor // Hybrid Signal Architecture")
with col2:
    st.markdown("### 🟢 LIVE" if data_available else "### 🔴 OFFLINE")

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
        use_container_width=True,
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