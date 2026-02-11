# Strategic Vision & Product Roadmap

## 1. Core Philosophy: Infrastructure-First, Agnostic Design
The primary goal of this project is to build a **High-Performance Data Platform**. The architecture is domain-agnostic, allowing the underlying data infrastructure to remain robust even if business logic pivots.

## 2. Business Problem: Block Space Efficiency
The project addresses the auction market for Bitcoin block space.
- **The Pain:** Overpaying fees due to market panic or capital loss in inefficient UTXO management.
- **The Solution:** An autonomous decision engine using real-time data to optimize treasury operations.

## 3. Pivot Options (The "Unicorn" Flexibility)

| Strategy              | Focus                             | Data Type                     |
|-----------------------|-----------------------------------|-------------------------------|
| **A: Fee Optimizer**  | Real-time bidding (RBF/CPFP)      | Streaming (Mempool)           |
| **B: Dust Sweeper**   | UTXO consolidation & risk mgmt    | Batch/Analytical (UTXO Set)   |
| **C: L2 Router**      | Liquidity & Routing optimization  | Graph/Network (Lightning/Ark) |

## 4. Phased Roadmap (2026)

### Phase 1: Foundation — ✅ COMPLETED
- **Architecture:** Decoupled Monorepo & Hybrid Infrastructure (Local + Docker).
- **AI Strategy:** Neuro-Symbolic Brain (Python Logic + Llama 3.2 Narrative).
- **Data Isolation:** Strict RO/RW separation with Docker volume permissions.

### Phase 2: Financial Hardening & Validation — 🔄 Q1 2026
- **[Critical] Schema Fix:** Refactor `float` to `int` (Satoshis) in all Pydantic models to prevent floating-point precision errors in financial computations.
- **[Analytics] Scientific Backtesting:**
    - **Metric:** Slippage / Opportunity Cost (Did we save sats vs the market?).
    - **Baseline:** Compare our "20% Premium" strategy against Simple Moving Averages (SMA/EMA). We must beat the index.
- **[Data] Lookback Strategy:** Ingest last 144 blocks (~24h) via REST API on boot.
    - **Impact:** ~7MB disk, ~5s boot time. Non-destructive (backfill only).

### Phase 3: The Prescriptive Operator — 🛠️ Q2 2026
- **Concept:** Move from Descriptive/Predictive to **Prescriptive Analytics**.
- **[Feature] Watchlist Module:** Allow tracking specific TXIDs (without wallet connection).
- **[Feature] RBF Advisor (Sender Strategy):** Alert if a tracked tx is stuck and calculate optimal replacement fee.
- **[Feature] CPFP Advisor (Receiver Strategy):** Alert if an incoming payment is stuck and calculate child-fee to unstick it.
- **[Feature] Dust Watch:** Alert when fees dip below 5 sats/vB for UTXO consolidation windows.

### Phase 4: Scalability & UX — ☁️ Q3 2026
- **[UI]** Migrate Streamlit to React/Next.js for complex interactivity.
- **[Decision] YAGNI:** No Repository Pattern and no Cloud LLM for now. Local DuckDB + Local Ollama is sufficient for the current scale.

### Phase 5: True Sovereignty — 🦁 Q4 2026 (Endgame)
- **[Infra]** Deploy Bitcoin Core Node (Pruned Mode, `prune=550`) in Docker.
- **[Backend]** Switch Ingestor from mempool.space API to Local RPC (`getblocktemplate`).
- **Goal:** Eliminate the "Black Box" dependency. Validate fees ourselves in a trustless way.

---
**Lead Engineer:** Israel (@ieshatchuell)
**Status:** Phase 2 Planning.