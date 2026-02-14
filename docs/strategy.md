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
- ~~**[Critical] Schema Fix:** Refactor `float` to `int` (Satoshis) in all Pydantic models~~ ✅ Done (ADR-007)
- ~~**[Data] Lookback Strategy:** Ingest last 144 blocks (~24h) via REST API on boot.~~ ✅ Done (ADR-008)
- ~~**[Data] Zero-Fee Block Filter:** Exclude miner-filled blocks (`median_fee = 0`) from historical baseline.~~ ✅ Done (ADR-008)
- ~~**[Fix] MinRelayFee Floor:** Enforce `max(1, round())` on `recommended_fee`.~~ ✅ Done (ADR-008)
- ~~**[UI] Dashboard Real Data:** Connect Streamlit to live DuckDB queries.~~ ✅ Done (ADR-008)
- ~~**[Analytics] Scientific Backtesting:**~~ ✅ Done (ADR-010)
    - **Result:** Orchestrator saves 27.7% vs market. Hit rate: 82%.
    - **Baseline:** 20% Premium beats SMA-20 (-0.5%) and EMA-20 (-4.9%).
- ~~**[UI] Strategy Simulator:** Interactive dashboard overlay comparing strategies against real block data.~~ ✅ Done (ADR-011)

### Phase 3: The Prescriptive Operator — 🛠️ Q2 2026
- **Concept:** Move from Descriptive/Predictive to **Prescriptive Analytics**.
- **[Core] Dual-Mode Strategy:** PATIENT (Orchestrator, -27.7%, for treasury) vs RELIABLE (EMA-20, -4.9%, for time-sensitive ops).
- **[Signal] EMA Hybrid:** Integrate EMA as secondary signal in orchestrator for urgency estimation.
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
**Status:** Phase 2 Completed ✅. Phase 3 next.