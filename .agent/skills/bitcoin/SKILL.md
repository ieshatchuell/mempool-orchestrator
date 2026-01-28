---
name: bitcoin-mempool-expert
description: Expert knowledge on Bitcoin data structures (Transactions, Blocks) and Mempool.space API patterns.
patterns: ["src/**/*.py", "tests/**/*.py"]
---

# Bitcoin & Mempool.space Domain Knowledge

## 1. Data Contracts (Immutable)

### Transaction Structure (REST API)
The `GET /api/block/:hash/txs` endpoint returns a list of Transaction objects.
**Critical Type Rules:**
- `value`: Always `int` (Satoshis). NEVER float.
- `fee`: Always `int` (Satoshis).
- `txid`: Hex string.

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
  "size": "int",
  "weight": "int",
  "fee": "int",
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

## 3. Libraries
Use pydantic v2 (BaseModel, Field, ConfigDict) for validation.

Use httpx for async HTTP requests (not requests).

