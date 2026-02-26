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

### Phase 6.5: UI Polish (Camino A) — 🛠️ NEXT
- **[DB] Add `pool_name`:** Add mining pool name column to `BlockRecord` ORM model.
- **[Consumer] Process `mempool_block` events:** Materialize projected blocks to compute the real **Median Fee Rate** instead of using `mempool_min_fee` as proxy.
- **[API] Enrich responses:** Populate `blocks_to_clear`, `fee_range`, and `pool_name` in API responses.

### Phase 7: The Brain (Camino B) — 🧠 PLANNED
- **[Worker] Reconnect `tx_hunter.py`:** Rewrite to consume from Kafka and populate the `advisories` table with RBF/CPFP recommendations.
- **[API] Wire Advisory Endpoints:** Connect watchlist GET/POST/DELETE to PostgreSQL.
- **[Feature] Automated Showcase:** Autonomous curation of "interesting" transactions.

### Phase 8: True Sovereignty — 🦁 Q4 2026 (Endgame)
- **[Infra]** Deploy Bitcoin Core Node (Pruned Mode, `prune=550`) in Docker.
- **[Backend]** Switch Ingestor from mempool.space API to Local RPC (`getblocktemplate`).
- **Goal:** Eliminate the "Black Box" dependency. Validate fees ourselves in a trustless way.

---
**Lead Engineer:** Israel (@ieshatchuell)
**Status:** Phase 5 (EDA Migration) COMPLETED ✅. Phase 6.5 (UI Polish) and Phase 7 (The Brain) next.