---
name: bitcoin-mempool-expert
description: Expert knowledge on Bitcoin data structures, Mempool APIs, and RBF/CPFP mechanics.
patterns: ["src/**/*.py", "tests/**/*.py"]
---

# Bitcoin & Mempool.space Domain Knowledge

## 1. Data Contracts (Immutable)

### Transaction Structure (REST API)
The `GET /api/block/:hash/txs` endpoint returns a list of Transaction objects.
**Critical Type Rules:**
- `value`: Always `int` (Satoshis). NEVER float.
- `fee`: Always `int` (Satoshis).
- `txid`: Hex string (64 chars).

**JSON Schema Reference:**
```json
{
  "txid": "string",
  "version": "int",
  "locktime": "int",
  "vin": [
    {
      "txid": "string",
      "vout": "int",
      "prevout": {
        "scriptpubkey_address": "string",
        "value": "int (satoshis)"
      },
      "scriptsig": "string",
      "witness": ["string"],
      "is_coinbase": "boolean",
      "sequence": "int"
    }
  ],
  "vout": [
    {
      "scriptpubkey_address": "string",
      "value": "int (satoshis)"
    }
  ],
  "size": "int (bytes)",
  "weight": "int (weight units)",
  "fee": "int (satoshis)",
  "status": {
    "confirmed": "boolean",
    "block_height": "int",
    "block_hash": "string",
    "block_time": "int"
  }
}
```

### WebSocket Block Signal
The WebSocket event block is strictly a SIGNAL. It does NOT contain transactions. Fields: id (hash), height, timestamp, tx_count, size, weight.

## 2. Infrastructure Constraints (Redpanda)
Hard Limit: 1,048,576 bytes (1MB) per Kafka message.

Pattern: Hybrid Ingestion.

Trigger: WebSocket block event.

Action: Async HTTP GET to fetch transactions.

Requirement: Transactions MUST be chunked into batches (e.g., 200 txs/batch) before producing to Kafka.

## 3. Protocol Mechanics (RBF & CPFP) - VITAL FOR ADVISORS

### A. Units & Conversions
**Source:** [BIP-141 (Segregated Witness)](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki)
- **Weight Units (WU):** The protocol's native size unit.
- **Virtual Bytes (vByte):** `vByte = WU / 4` (Standard definition).
- **Fee Rate:** `sat/vB = fee_sats / vSize_vBytes`.

### B. RBF (Replace-By-Fee) Rules
**Source:** [BIP-125 (Opt-in RBF)](https://github.com/bitcoin/bips/blob/master/bip-0125.mediawiki)
To replace a transaction, the new one must satisfy:
1.  **Absolute Fee Rule:** `NewFee > OriginalFee` (Must pay more total absolute fees).
2.  **Relay Fee Rule:** `NewFeeRate >= OriginalFeeRate + MinRelayTxFee` (Must pay for its own bandwidth).
    * *Standard:* MinRelayTxFee is typically **1 sat/vB**.
    * *Formula:* `TargetFee = max(MarketFeeRate, OriginalFeeRate + 1.0) * vSize`.

### C. CPFP (Child-Pays-For-Parent) Mechanics
**Source:** [Bitcoin Ops: CPFP & Package Relay](https://bitcoinops.org/en/topics/cpfp/)
Miners select transactions based on **Package Fee Rate** (Ancestry).
- **Goal:** Effective Fee Rate of the package (Parent + Child) >= Market Fee Rate.
- **Formula:**
  `PackageFeeRate = (ParentFee + ChildFee) / (ParentVSize + ChildVSize)`
- **Solving for Child Fee:**
  `ChildFee = (TargetRate * (ParentVSize + ChildVSize)) - ParentFee`

## 4. Libraries & Standards
Validation: Use pydantic v2 (BaseModel, Field, ConfigDict).

HTTP: Use httpx for async requests (blocking requests is banned).

Math: Use math.ceil() for fee calculations. Always round UP to ensure inclusion.