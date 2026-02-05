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
  - ✅ **PIVOTED:** Neuro-Symbolic Architecture (see below)

### Q1.6: Neuro-Symbolic AI Pivot - [COMPLETED]
- **Technical Goal:** Refactor Orchestrator from "Pure LLM Agent" to "Safe-Guarded Hybrid".
- **Business Goal:** Achieve 100% reliability and sub-second decision latency.
- **Status:**
  - ✅ Python logic layer for deterministic decisions (Layer 1)
  - ✅ LLM narrative layer for human-readable reasoning (Layer 2)
  - ✅ Performance: ~40s → ~1.3s (~30x improvement)
  - ✅ Graceful degradation when AI is unavailable

#### Strategy Rules (Deterministic - Python)

The decision strategy is now **code**, not prompts:

| Condition | Action | Target Fee |
|-----------|--------|------------|
| `fee_premium_pct > 20%` | **WAIT** | Historical Median Fee |
| `fee_premium_pct <= 20%` | **BROADCAST** | Current Median Fee |

> **Key Insight:** The LLM never makes decisions. It only explains why the Python-computed decision makes sense.

### Q2: The Memory (Modeling & Intelligence)
- **Technical Goal:** Advanced transaction parsing and historical trend analysis.
- **Business Goal:** Identify fee-saving patterns and whale movement detection.

### Q3: Advanced Orchestration
- **Technical Goal:** Multi-strategy support, RBF/CPFP automation.
- **Business Goal:** Transition from "Observer" to active "Treasury Operator".

---
**Lead Engineer:** Israel (@ieshatchuell)
**Status:** Phase 2.5 Neuro-Symbolic Pivot Complete.