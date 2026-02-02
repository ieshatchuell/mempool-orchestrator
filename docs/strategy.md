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

### Q1: The Backbone (Infrastructure & Ingestion) - [COMPLETED]
- **Technical Goal:** Deploy a resilient pipeline (Redpanda + Python/uv + DuckDB).
- **Business Goal:** Achieve "Full Observability" via structured Medallion layers (Bronze/Silver).
- **Status:** 
  - ✅ Ingestion pipeline (WebSocket + REST API)
  - ✅ Typed storage layer with Pydantic validation
  - ✅ Data quality hardening (schema relaxation for API compatibility)
  - ✅ Analytics dashboard for real-time observability
  - ✅ Storage schema evolution (`block_index` ordering, `fee_range` arrays)

### Q1.5: The Agentic Brain (Infrastructure) - [COMPLETED]
- **Technical Goal:** Deploy local LLM infrastructure (Ollama + Llama 3.2) and AI Orchestrator service.
- **Business Goal:** Enable AI-driven analysis of mempool data with structured reasoning.
- **Status:**
  - ✅ Ollama service in Docker with model persistence
  - ✅ AI Orchestrator with read-only DuckDB access
  - ✅ Hybrid architecture (local writer + containerized reader)
  - ✅ PydanticAI integration for agentic workflows
  - ⏳ **Next:** Develop PydanticAI Skills/Tools for mempool analysis

### Q2: The Memory (Modeling & Intelligence)
- **Technical Goal:** Advanced transaction parsing and historical trend analysis.
- **Business Goal:** Identify fee-saving patterns and whale movement detection.

### Q3: The Intelligence (Agentic Decision Layer)
- **Technical Goal:** Integrate LLMs as reasoning engines for autonomous bidding.
- **Business Goal:** Transition from "Observer" to "Orchestrator".

---
**Lead Engineer:** Israel (@ieshatchuell)
**Status:** Phase 2 Agentic Brain Infrastructure Complete.