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

### Phase 2: Financial Hardening & Validation — ✅ COMPLETED
- ~~**[Critical] Schema Fix:** Refactor `float` to `int` (Satoshis) in all Pydantic models~~ ✅ Done (ADR-007)
- ~~**[Data] Lookback Strategy:** Ingest last 144 blocks (~24h) via REST API on boot.~~ ✅ Done (ADR-008)
- ~~**[Data] Zero-Fee Block Filter:** Exclude miner-filled blocks from historical baseline.~~ ✅ Done (ADR-008)
- ~~**[Fix] MinRelayFee Floor:** Enforce `max(1, round())` on `recommended_fee`.~~ ✅ Done (ADR-008)
- ~~**[Analytics] Scientific Backtesting:**~~ ✅ Done (ADR-010)
    - **Result:** Orchestrator saves 27.7% vs market. Hit rate: 82%.
- ~~**[UI] Strategy Simulator:** Interactive dashboard overlay.~~ ✅ Done (ADR-011)

### Phase 3: The Prescriptive Operator — ✅ COMPLETED
- ~~**[Core] Dual-Mode Strategy:** PATIENT vs RELIABLE.~~ ✅ Done (ADR-012)
- ~~**[Signal] EMA Hybrid:** Integrate EMA as secondary signal.~~ ✅ Done (ADR-012)
- ~~**[Feature] Watchlist Module:** Track specific TXIDs.~~ ✅ Done (ADR-013)
- ~~**[Feature] RBF Advisor (Sender Strategy).~~ ✅ Done (ADR-014)
- ~~**[Feature] CPFP Advisor (Receiver Strategy).~~ ✅ Done (ADR-014)

### Phase 4: UI Migration — ✅ COMPLETED
- ~~**[UI]** Migrate Streamlit to React/Next.js.~~ ✅ Done
- **[Pivot] Automated Showcase:** Read-only showcase of "interesting" transactions. (ADR-015)

### Phase 5: EDA Migration — ✅ COMPLETED (ADR-016)
- ~~**[Infra] Stack Migration:** DuckDB+Redis → PostgreSQL.~~ ✅ Done
- ~~**[Infra] Messaging:** confluent-kafka (sync) → aiokafka (async).~~ ✅ Done
- ~~**[Arch] Clean Architecture:** Hexagonal layers (domain/infrastructure/workers/api).~~ ✅ Done
- ~~**[Workers] Ingestor:** Reconnected to async producer.~~ ✅ Done
- ~~**[Workers] State Consumer:** Kafka → PostgreSQL materializer.~~ ✅ Done
- ~~**[API] Presentation Layer:** Async SQLAlchemy read-only queries.~~ ✅ Done
- ~~**[Scripts] Backfill:** 144-block initial load from REST API.~~ ✅ Done

### Phase 6.5: Governance, Infrastructure & UI Polish — ✅ COMPLETED (Session 6)
- ~~**[Governance] Git Workflow:** Branching rule enforced in agent persona.~~ ✅ Done
- ~~**[Infra] pgAdmin:** Database viewer service with env var interpolation.~~ ✅ Done
- ~~**[DB] Schema Enrichment:** `pool_name` (VARCHAR) + `fee_range` (JSONB) on blocks. New `mempool_block_projections` table.~~ ✅ Done
- ~~**[Consumer] Snapshot Pattern:** `mempool_block` events materialized via DELETE + INSERT.~~ ✅ Done
- ~~**[API] Enrich Responses:** Real `pool_name`, `fee_range`, `blocks_to_clear`.~~ ✅ Done
- ~~**[QA] Test Suite:** 47 tests (all green). Legacy tests fixed.~~ ✅ Done
- ~~**[Cleanup] Logic Migration:** Orchestrator Docker container removed. Market analytics (EMA, Trend, Strategy) migrated to inline `query_orchestrator_status()` in API layer.~~ ✅ Done
- ~~**[Docs] Full Update:** README, architecture.md, strategy.md updated.~~ ✅ Done

### Phase 7: The Brain (Camino B) — 🧠 PLANNED
- **[Worker] Reconnect `tx_hunter.py`:** Rewrite to consume from Kafka and populate the `advisories` table with RBF/CPFP recommendations.
- **[API] Wire Advisory Endpoints:** Connect watchlist GET/POST/DELETE to PostgreSQL.
- **[Feature] Automated Showcase:** Autonomous curation of "interesting" transactions.

### Session 7: Frontend Polish & Visualization — ✅ COMPLETED (ADR-020)
- ~~**[UI] Fee Histograms:** Recharts bar chart for 7-band `fee_range` distribution.~~ ✅ Done
- ~~**[UI] Block Weight Chart:** Horizontal fullness bars with pool badges and color-coded capacity.~~ ✅ Done
- ~~**[UI] Table Micro-Viz:** Inline fee range gradient bar + colored pool name badges.~~ ✅ Done
- ~~**[UI] CSS Animations:** `fade-in-up` keyframes, stagger delays (60ms), `hover-lift` on cards.~~ ✅ Done
- ~~**[Docs] Architecture Diagram:** Rewrote Mermaid diagram — strict `graph TD`, color-coded layers, no spaghetti.~~ ✅ Done
- ~~**[QA] Type Safety Audit:** `types.ts` ↔ `schemas.py` — all 4 endpoints verified in sync.~~ ✅ Done

### Session 8: The Brain & Logic Hardening — 🧠 NEXT
- **[Logic] Confidence Calculation:** Replace hardcoded confidence values (0.5/0.8) in `query_orchestrator_status()` with real EMA-based logic. Currently a hotfix.
- **[Data] Auto-Backfill on Boot:** Implement backfill trigger when charts detect data gaps. Resolve "Premium -100%" edge case (snapshot `median_fee = 0.0`).
- **[UX] Info Tooltips:** Add `ⓘ` button to each KPI card and chart with brief explainers (what it is, why it matters, how it's calculated).
- **[Worker] `tx_hunter.py` — Advisory Engine:** Rewrite to PostgreSQL + REST polling. Study feasibility and cost of real-time advisory features before committing to implementation scope.

### Phase 8: True Sovereignty — 🦁 Q4 2026 (Endgame)
- **[Infra]** Deploy Bitcoin Core Node (Pruned Mode, `prune=550`) in Docker.
- **[Backend]** Switch Ingestor from mempool.space API to Local RPC (`getblocktemplate`).
- **Goal:** Eliminate the "Black Box" dependency. Validate fees ourselves in a trustless way.

---
**Lead Engineer:** Israel (@ieshatchuell)
**Status:** Session 7 (Frontend Polish & Visualization) COMPLETED ✅. Session 8 (The Brain & Logic Hardening) next.