# Data Dictionary & Lineage

**Scope:** End-to-end data lineage for the Mempool Orchestrator Dashboard.
**Purpose:** Single source of truth for metric definitions, calculations, and data provenance.

## 1. Fundamental Concepts: The Block Space Market

The Orchestrator monitors the **global auction for censorship-resistant block space**.

### A. Mempool (The Order Book / Demand)
* **Definition:** The dynamic set of valid, unconfirmed transactions broadcasting their bid (fee) to network validators. It represents **instantaneous market intent**.
* **Nature:** Volatile, probabilistic, and high-frequency.
* **Data Source:** WebSocket Stream.
    * `stats`: Global aggregate data (Total fees, count).
    * `mempool-blocks`: Project blocks (Candidate templates).
* **Comparison Logic:** We compare **Snapshot vs. Snapshot** to measure congestion trends (e.g., Queue depth now vs. Queue depth 1h ago).

### B. Blockchain (The Settlement Log / Supply)
* **Definition:** The immutable history of transactions that won the auction and were finalized via Proof-of-Work.
* **Nature:** Static, ordered, and final.
* **Data Source:**
    * `blocks` (WebSocket Channel): The signal trigger (hash/height) when a new block is mined.
    * REST API (`GET /api/v1/block/...`): Fetches full settlement details triggered by the signal.

---

## 2. Metric Inventory

### A. Core KPIs (The Live Auction)
*Visual location: Top cards row.*

| Metric | Source (Raw) | Persistence (DB) | Type & Unit | Logic / Transformation | Frequency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mempool Size** | `mempoolInfo.size` | `mempool_snapshots.tx_count` | `INT` (Count) | Direct mapping. Total unconfirmed bids. | **5s** (Polling) |
| **Median Fee Rate** | `mempool-blocks[0].medianFee` | `mempool_snapshots.median_fee` | `FLOAT` (sat/vB) | **Enrichment:** Extracted from Candidate Block #0 (Clearing price). Fallback: 1.0. | **5s** (Polling) |
| **Pending Fees** | `mempoolInfo.totalFee` | `mempool_snapshots.total_fee_sats` | `INT` (Satoshis) | **Conversion:** API sends BTC. Converted: `round(BTC * 1e8)`. | **5s** (Polling) |
| **Blocks to Clear** | `mempool_snapshots.total_bytes` | Computed on-the-fly | `INT` (Count) | `math.ceil(total_bytes / 1_000_000)`. True Backlog — bypasses API's 8-block cap (ADR-022). | **On-Request** |
| **Delta (1h)** | `Snapshot` vs `Snapshot -1h` | `mempool_snapshots` | `FLOAT` (%) | `((Current - Old) / Old) * 100`. Returns `N/A` if `Old=0` or if historical snapshot is less than 30 minutes old (delta gate — ensures meaningful comparison). | **On-Request** |

### B. Market Intelligence (The Brain)
*Visual location: "Strategy & Trend" Card.*

| Metric | Inputs | Computation Logic | Frequency |
| :--- | :--- | :--- | :--- |
| **Fee Premium** | `Current Median`<br>`Hist Median` | `((Current - Hist) / Hist) * 100`<br>Guard: 0.0% if inputs <= 0. | **10s** (Polling) |
| **EMA Trend** | `EMA-20 (Current)`<br>`EMA-20 (Lag-5)` | `((EMA_Now - EMA_Prev) / EMA_Prev) * 100`<br>`> +5%` = RISING, `< -5%` = FALLING. | **10s** (Polling) |
| **Confidence** | `Trend`, `Premium`, `Divergence` | **4-Signal Model (Pure Python):**<br>Base 0.5 ± adjustments from: (1) EMA trend direction, (2) fee premium magnitude, (3) current-vs-EMA divergence ratio, (4) mode-specific weighting (Patient vs Fast).<br>Clamped `[0.10, 0.95]`. | **10s** (Polling) |

### C. Fee Advisors (The Sniper)
*Visual location: "Fee Advisors" List.*

| Advisor | Role | Formula (Satoshis) | Constraint | Frequency |
| :--- | :--- | :--- | :--- | :--- |
| **RBF** | Sender | `max(TargetRate, OriginalRate + 1.0) * TxVSize`; then `max(result, original_fee + 1)` | BIP-125: must exceed both original fee rate + relay AND absolute original fee. | **60s** (Worker) / **15s** (UI Poll) |
| **CPFP** | Receiver | `(TargetRate * (ParentSize + ChildSize)) - ParentFee` | Child pays deficit for Parent. Minimum 1 sat. | **60s** (Worker) / **15s** (UI Poll) |

### D. Settlement Data (The Ledger)
*Visual location: Charts & "Recent Blocks" Table.*

| Metric | Source | Persistence (DB) | Logic / Visualization | Frequency |
| :--- | :--- | :--- | :--- | :--- |
| **Block Weight** | `block.size` | `blocks.size` | `% Fullness = (Size / 4,000,000) * 100`. | **30s** (Polling) |
| **Fee Dist.** | `block.extras.feeRange` | `blocks.fee_range` | JSONB Array of 7 percentiles used for Heatmap. | **30s** (Polling) |
| **Recent Blocks** | `GET /api/blocks/recent` | `blocks` table | **8 Columns:**<br>1. **Height** (PK)<br>2. **Time** (Mined at)<br>3. **Transactions** (Count)<br>4. **Size** (MB)<br>5. **Fee Range** (Min-Max bars)<br>6. **Median Fee** (sat/vB)<br>7. **Total Fees** (BTC)<br>8. **Miner** (Pool Name) | **30s** (Polling) |
