# Strategic Vision & Product Roadmap

## 1. Core Philosophy: Infrastructure-First, Agnostic Design
The primary goal of this project is to build a **High-Performance Data Platform**, not just a single-purpose Bitcoin tool. The architecture is designed to be domain-agnostic, allowing the business logic to pivot while the underlying data infrastructure remains robust.

### Why Mempool as "Hard Mode"?
We chose the Bitcoin Mempool as the initial data source because it represents the most challenging real-time data environment:
- **High Velocity:** Thousands of events per second.
- **Financial Criticality:** Every byte has a direct economic cost.
- **Zero Downtime:** The network operates 24/7.

*Success in the Mempool layer proves the platform can handle any institutional-grade data workload.*

## 2. Business Problem: Block Space Efficiency
The project addresses the inefficiency of the block space auction market. 
- **The Pain:** Corporations overpay fees due to panic or lose capital in "dust" UTXOs.
- **The Solution:** An autonomous decision engine that uses real-time data to optimize treasury operations.

## 3. Pivot Options (The "Unicorn" Flexibility)
The platform is built to support three potential business pivots without re-engineering the core:

|-----------------------|-----------------------------------|-------------------------------|
| Strategy              | Focus                             | Data Type                     |
|-----------------------|-----------------------------------|-------------------------------|
| **A: Fee Optimizer**  | Real-time bidding (RBF/CPFP)      | Streaming (Mempool)           |
| **B: Dust Sweeper**   | UTXO consolidation & risk mgmt    | Batch/Analytical (UTXO Set)   |
| **C: L2 Router**      | Liquidity & Routing optimization  | Graph/Network (Lightning/Ark) |
|-----------------------|-----------------------------------|-------------------------------|

## 4. Phased Roadmap (2026)

### Q1: The Backbone (Infrastructure & Ingestion)
- **Technical Goal:** Deploy a resilient pipeline (Redpanda + Python/uv + Docker).
- **Business Goal:** Achieve "Full Observability" of the live auction market (Mempool).

### Q2: The Memory (Modeling & Storage)
- **Technical Goal:** Implement DuckDB for high-speed OLAP analytics.
- **Business Goal:** Historical analysis of fee trends to identify saving patterns.

### Q3: The Intelligence (Agentic Decision Layer)
- **Technical Goal:** Integrate LLMs as reasoning engines for autonomous action.
- **Business Goal:** Transition from "Observer" to "Orchestrator" (Autonomous Treasury).

---
**Lead Engineer:** Israel (@ieshatchuell)
**Status:** Strategic Alignment Confirmed.