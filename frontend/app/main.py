import os
import streamlit as st
import pandas as pd
import numpy as np
import duckdb
from dotenv import load_dotenv

# Load environment variables from root .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

# Configuration via environment variables (fully decoupled from backend)
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "../data/market/mempool_data.duckdb")

# --- CONFIGURACIÓN DE PÁGINA (ESTÉTICA DARK) ---
st.set_page_config(
    page_title="Mempool Orchestrator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Hack para forzar colores "Cypherpunk"
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

# --- CABECERA ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("⚡ MEMPOOL ORCHESTRATOR_")
    st.caption("Real-time Auditor // Hybrid Signal Architecture")
with col2:
    st.markdown("### 🔴 LIVE")

st.divider()

# --- FILA 1: KPIs (THE PULSE) ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(label="MEMPOOL SIZE (vMB)", value="412.5 MB", delta="12.5 MB")
kpi2.metric(label="MEDIAN FEE (sat/vB)", value="45", delta="-2")
kpi3.metric(label="PENDING FEES (BTC)", value="3.45 BTC", delta="0.12 BTC")
kpi4.metric(label="BLOCKS TO CLEAR", value="24", delta="1")

# --- FILA 2: AUDITORÍA (LO QUE VAMOS A CONSTRUIR) ---
st.subheader("🛡️ BLOCK AUDIT // PROJECTION vs REALITY")

# Datos falsos para simular el "Auditor"
data = {
    "Block Height": [882105, 882104, 882103, 882102, 882101],
    "Projected Fee (sats)": [45, 50, 12, 10, 55],
    "Actual Fee (sats)": [48, 49, 25, 10, 60],
    "Miner": ["Foundry USA", "AntPool", "ViaBTC", "F2Pool", "Mara"],
    "Status": ["CONFIRMED", "CONFIRMED", "CONFIRMED", "CONFIRMED", "CONFIRMED"]
}
df = pd.read_json(pd.DataFrame(data).to_json())

# Calcular el Slippage (Error de predicción)
df["Slippage %"] = ((df["Actual Fee (sats)"] - df["Projected Fee (sats)"]) / df["Projected Fee (sats)"] * 100).round(1)

# Función para colorear el slippage
def highlight_slippage(val):
    color = '#ff4b4b' if abs(val) > 10 else '#00FF41' # Rojo si error > 10%, Verde si ok
    return f'color: {color}'

st.dataframe(
    df.style.map(highlight_slippage, subset=['Slippage %']),
    use_container_width=True,
    hide_index=True
)

# --- FILA 3: GRÁFICO DE TENDENCIA ---
st.subheader("📈 FEE TREND (LAST 1H)")
chart_data = pd.DataFrame(
    np.random.randn(20, 2) + [50, 50],
    columns=['Projected', 'Real']
)
st.line_chart(chart_data, color=["#F7931A", "#00FF41"]) # Naranja (Projected), Verde (Real)