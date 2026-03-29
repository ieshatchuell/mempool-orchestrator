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
- **AI Strategy:** Deterministic Python logic (Llama 3.2 removed — ADR-016/019).
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
- ~~**[Core] Dual-Mode Strategy:** PATIENT vs FAST (renamed from RELIABLE — Session 11).~~ ✅ Done (ADR-012)
- ~~**[Signal] EMA Hybrid:** Integrate EMA as secondary signal.~~ ✅ Done (ADR-012)
- ~~**[Feature] Watchlist Module:** Track specific TXIDs.~~ ✅ Done (ADR-013)
- ~~**[Feature] RBF Advisor (Sender Strategy).~~ ✅ Done (ADR-014)
- ~~**[Feature] CPFP Advisor (Receiver Strategy).~~ ✅ Done (ADR-014)

### Phase 4: UI Migration — ✅ COMPLETED
- ~~**[UI]** Migrate Streamlit to React/Next.js.~~ ✅ Done
- ~~**[Pivot] Automated Showcase:** Read-only showcase of "interesting" transactions. (ADR-015)~~ ✅ Done

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
- ~~**[Consumer] UPSERT Pattern:** `mempool_block` events materialized via UPSERT + orphan cleanup on UNLOGGED table.~~ ✅ Done
- ~~**[API] Enrich Responses:** Real `pool_name`, `fee_range`, `blocks_to_clear`.~~ ✅ Done
- ~~**[QA] Test Suite:** 47 tests (all green). Legacy tests fixed.~~ ✅ Done
- ~~**[Cleanup] Logic Migration:** Orchestrator Docker container removed. Market analytics (EMA, Trend, Strategy) migrated to inline `query_orchestrator_status()` in API layer.~~ ✅ Done
- ~~**[Docs] Full Update:** README, architecture.md, strategy.md updated.~~ ✅ Done

### Phase 7: The Brain & UI Maturity — ✅ COMPLETED

#### Session 7: Frontend Polish & Visualization (ADR-020)
- ~~**[UI] Fee Histograms:** Recharts bar chart for 7-band `fee_range` distribution.~~ ✅ Done
- ~~**[UI] Block Weight Chart:** Horizontal fullness bars with pool badges and color-coded capacity.~~ ✅ Done
- ~~**[UI] Table Micro-Viz:** Inline fee range gradient bar + colored pool name badges.~~ ✅ Done
- ~~**[UI] CSS Animations:** `fade-in-up` keyframes, stagger delays (60ms), `hover-lift` on cards.~~ ✅ Done
- ~~**[Docs] Architecture Diagram:** Rewrote Mermaid diagram — strict `graph TD`, color-coded layers, no spaghetti.~~ ✅ Done
- ~~**[QA] Type Safety Audit:** `types.ts` ↔ `schemas.py` — all 4 endpoints verified in sync.~~ ✅ Done

#### Session 8: The Brain & Logic Hardening
- ~~**[Data] Auto-Backfill on Boot:** Incremental gap detection in `src/workers/backfill.py`, triggered in API lifespan (non-fatal). `scripts/backfill_blocks.py` deprecated.~~ ✅ Done
- ~~**[Logic] Confidence Calculation:** `_compute_confidence()` replaces hardcoded 0.5/0.8 with real EMA divergence + trend + premium signals.~~ ✅ Done
- ~~**[Fix] Premium -100%:** Guard clause for `current_median_fee <= 0` in `query_orchestrator_status()`.~~ ✅ Done
- ~~**[UX] Info Tooltips:** `ⓘ` HoverCard on all KPI cards, Fee Histogram, and Block Weight chart.~~ ✅ Done
- ~~**[Worker] Advisory Engine:** `tx_hunter.py` rewritten — polls `/api/mempool/recent`, calculates BIP-125 RBF + CPFP fees, writes to `advisories` table.~~ ✅ Done
- ~~**[API] Wire Watchlist:** `query_watchlist_advisories()` reads real `AdvisoryRecord` data from PostgreSQL.~~ ✅ Done
- ~~**[QA] Test Suite:** 74 tests (all green). 27 new tests (backfill: 6, queries: 11, tx_hunter: 10).~~ ✅ Done

#### Session 9: Data Dictionary & UX Refactor
- ~~**[Docs] Data Dictionary:** Created `docs/data_dictionary.md` — single source of truth for metric definitions, calculations, lineage, and frequencies.~~ ✅ Done
- ~~**[Docs] Data Governance:** Cross-reference added to `docs/architecture.md` (Section 8).~~ ✅ Done
- ~~**[UX] Dashboard Layout Refactor:** Split `page.tsx` into two conceptual zones: "Live Market Dynamics" (KPIs, Advisors, Strategy) and "Settlement History" (Charts, Recent Blocks).~~ ✅ Done
- ~~**[UX] Scanner Mode:** Advisors panel converted to read-only (removed manual TXID input/delete). Added `Badge` ("Live Scanning") + info tooltip.~~ ✅ Done
- ~~**[UX] Info Tooltips:** Added to Strategy & Trend panel and Recent Blocks table headers.~~ ✅ Done
- ~~**[UX] Visual Atmosphere:** Indigo radial glow (Live zone) + Amber radial glow (Settlement zone) + pulse indicator on Live header.~~ ✅ Done

#### Session 10: UI Cleanup & True Backlog KPI
- ~~**[KPI] True Backlog:** `blocks_to_clear` switched from `COUNT(*)` (capped at 8) to `math.ceil(total_bytes / 1MB)` — on-the-fly in `queries.py`, no schema changes.~~ ✅ Done (ADR-022)
- ~~**[UI] Layout Containment:** Removed amber glow (visual bleed issues). Simplified separator spacing (`mt-8`). Settlement section uses clean layout.~~ ✅ Done (ADR-023)

#### Session 11: i18n Integration & UX Friction Fixes
- ~~**[i18n] Full Integration:** EN/ES toggle, all 9 dashboard components wired to `useTranslations()`.~~ ✅ Done
- ~~**[UX] Reliable → Fast Rename:** Semantic rename across dictionaries, strategy-panel, advisors-panel, status-bar.~~ ✅ Done
- ~~**[UX] Mining Pool Links:** PoolBadge clickable → `mempool.space/mining/pool/{name}`. Unknown pools hidden.~~ ✅ Done
- ~~**[Backend] Advisory i18n:** Backend sends `target_fee_rate` (structured) instead of English strings. Frontend formats with templates.~~ ✅ Done
- ~~**[Backend] KPI Delta Gate:** 30-minute minimum gap for historical deltas — returns N/A when data is insufficient.~~ ✅ Done
- ~~**[UX] Dynamic Value Translations:** Footer actions (WAIT/BROADCAST), traffic levels, EMA trends all translated.~~ ✅ Done
- ~~**[Docs] Architecture Overhaul:** 14-point remediation of `architecture.md` — all diagrams and tables synchronized.~~ ✅ Done

### Phase 8: Full Containerization — ✅ COMPLETED
- **[Infra]** Eradicated local host execution; unified microservices cluster under `docker-compose.yml`.
- **[Deploy]** Standardized DX with pure Docker build commands and strict healthchecks.

### Phase 9: Advanced RBF/CPFP Refinement — 🚀 NEXT
- **[Logic]** Deep analytical refinement of the RBF/CPFP decision engine.
- **[Goal]** Maximize Fee Fairness by optimizing the consensus rule engine beyond current baseline estimations.

### Phase 10: True Sovereignty — 🦁 Q4 2026 (Endgame)
- **[Infra]** Deploy Bitcoin Core Node (Pruned Mode, `prune=550`) in Docker.
- **[Backend]** Switch Ingestor from mempool.space API to Local RPC (`getblocktemplate`).
- **Goal:** Eliminate the "Black Box" dependency. Validate fees ourselves in a trustless way.

---
**Lead Engineer:** Israel (@ieshatchuell)
**Status:** Phase 8 (Full Containerization) COMPLETED ✅. Phase 9 (Advanced RBF/CPFP Refinement) next.