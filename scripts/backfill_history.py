#!/usr/bin/env python3
"""Backfill ~24h of historical block data into DuckDB.

Fetches the latest 144 confirmed blocks from mempool.space REST API
and a current mempool snapshot. Inserts data into the same tables
used by the live WebSocket pipeline, enabling immediate system testing
without waiting for real-time ingestion.

Usage:
    python scripts/backfill_history.py
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import httpx

# ─── Configuration ───────────────────────────────────────────────────────────
API_BASE = "https://mempool.space/api"
BLOCKS_PER_PAGE = 15  # API returns 15 blocks per call
TARGET_BLOCKS = 144   # ~24 hours of blocks (1 block ≈ 10 min)
DB_PATH = Path(__file__).parent.parent / "data" / "market" / "mempool_data.duckdb"
REQUEST_DELAY = 1.0   # Seconds between API calls (rate limiting)


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    """Create tables if they don't exist (idempotent)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mempool_stats (
            ingestion_time TIMESTAMP NOT NULL,
            size UINTEGER NOT NULL,
            bytes UINTEGER NOT NULL,
            total_fee UBIGINT NOT NULL,
            min_fee DOUBLE NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projected_blocks (
            ingestion_time TIMESTAMP NOT NULL,
            block_index UTINYINT NOT NULL,
            block_size UINTEGER NOT NULL,
            block_v_size DOUBLE NOT NULL,
            n_tx UINTEGER NOT NULL,
            total_fees UBIGINT NOT NULL,
            median_fee DOUBLE NOT NULL,
            fee_range JSON NOT NULL
        )
    """)


def fetch_blocks(client: httpx.Client, target: int) -> list[dict]:
    """Fetch `target` confirmed blocks, paginating by startHeight."""
    all_blocks: list[dict] = []
    start_height: int | None = None

    while len(all_blocks) < target:
        if start_height is None:
            url = f"{API_BASE}/v1/blocks"
        else:
            url = f"{API_BASE}/v1/blocks/{start_height}"

        print(f"  📡 Fetching blocks from height {start_height or 'tip'}...")
        resp = client.get(url, timeout=30)
        resp.raise_for_status()

        page = resp.json()
        if not page:
            print("  ⚠️  No more blocks returned, stopping.")
            break

        all_blocks.extend(page)

        # Next page starts from height *before* the last block in this page
        start_height = page[-1]["height"] - 1

        remaining = target - len(all_blocks)
        if remaining > 0:
            time.sleep(REQUEST_DELAY)

    return all_blocks[:target]


def fetch_mempool_snapshot(client: httpx.Client) -> dict:
    """Fetch current mempool statistics."""
    print("  📡 Fetching current mempool snapshot...")
    resp = client.get(f"{API_BASE}/mempool", timeout=30)
    resp.raise_for_status()
    return resp.json()


def insert_blocks(conn: duckdb.DuckDBPyConnection, blocks: list[dict]) -> int:
    """Insert confirmed blocks into projected_blocks table."""
    rows_inserted = 0

    for block in blocks:
        extras = block.get("extras", {})

        # Use block timestamp as ingestion_time
        block_time = datetime.fromtimestamp(block["timestamp"], tz=timezone.utc)

        # Map confirmed block fields to projected_blocks schema
        record = (
            block_time,
            0,  # block_index: confirmed block = "next block" that was mined
            block["size"],
            extras.get("virtualSize", 0.0),
            block["tx_count"],
            extras.get("totalFees", 0),     # Already int Satoshis
            extras.get("medianFee", 0.0),   # sat/vB
            json.dumps(extras.get("feeRange", [])),
        )

        conn.execute(
            "INSERT INTO projected_blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            list(record),
        )
        rows_inserted += 1

    return rows_inserted


def insert_mempool_snapshot(conn: duckdb.DuckDBPyConnection, snapshot: dict) -> None:
    """Insert mempool snapshot into mempool_stats table."""
    now = datetime.now(timezone.utc)

    # Extract min fee from fee_histogram (first bucket's rate)
    fee_histogram = snapshot.get("fee_histogram", [])
    min_fee = fee_histogram[-1][0] if fee_histogram else 0.0

    record = (
        now,
        snapshot["count"],          # Transaction count → size
        snapshot["vsize"],          # Virtual size → bytes
        snapshot["total_fee"],      # Already int Satoshis from this endpoint
        min_fee,
    )

    conn.execute(
        "INSERT INTO mempool_stats VALUES (?, ?, ?, ?, ?)",
        list(record),
    )


def verify_data(conn: duckdb.DuckDBPyConnection) -> None:
    """Print verification queries."""
    print("\n" + "=" * 60)
    print("📊 VERIFICATION: mempool_stats")
    print("=" * 60)

    stats_count = conn.execute("SELECT COUNT(*) FROM mempool_stats").fetchone()[0]
    print(f"Total rows: {stats_count}")

    rows = conn.execute(
        "SELECT * FROM mempool_stats ORDER BY ingestion_time DESC LIMIT 5"
    ).fetchall()
    columns = ["ingestion_time", "size", "bytes", "total_fee", "min_fee"]
    print(f"\n{'  '.join(f'{c:<16}' for c in columns)}")
    print("-" * 80)
    for row in rows:
        print(f"  {row}")

    print("\n" + "=" * 60)
    print("📊 VERIFICATION: projected_blocks")
    print("=" * 60)

    blocks_count = conn.execute("SELECT COUNT(*) FROM projected_blocks").fetchone()[0]
    print(f"Total rows: {blocks_count}")

    rows = conn.execute(
        "SELECT ingestion_time, block_index, block_size, n_tx, total_fees, median_fee "
        "FROM projected_blocks ORDER BY ingestion_time DESC LIMIT 5"
    ).fetchall()
    columns = ["ingestion_time", "idx", "block_size", "n_tx", "total_fees", "median_fee"]
    print(f"\n{'  '.join(f'{c:<16}' for c in columns)}")
    print("-" * 96)
    for row in rows:
        print(f"  {row}")

    # Show historical median (what the orchestrator would compute)
    hist_median = conn.execute("""
        SELECT MEDIAN(median_fee) FROM (
            SELECT median_fee FROM projected_blocks
            WHERE block_index = 0
            ORDER BY ingestion_time DESC
            LIMIT 100
        )
    """).fetchone()[0]
    print(f"\n🎯 Historical Median Fee (last 100 blocks): {hist_median:.2f} sat/vB")


def main():
    print("🚀 Mempool Backfill: Lookback Strategy")
    print(f"   Database: {DB_PATH}")
    print(f"   Target: {TARGET_BLOCKS} blocks (~24h)")
    print()

    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(DB_PATH))

    try:
        init_db(conn)

        with httpx.Client() as client:
            # 1. Fetch and insert confirmed blocks
            print("📦 Phase 1: Fetching confirmed blocks...")
            blocks = fetch_blocks(client, TARGET_BLOCKS)
            rows = insert_blocks(conn, blocks)
            print(f"   ✅ Inserted {rows} blocks into projected_blocks\n")

            # 2. Fetch and insert mempool snapshot
            print("📦 Phase 2: Fetching mempool snapshot...")
            snapshot = fetch_mempool_snapshot(client)
            insert_mempool_snapshot(conn, snapshot)
            print(f"   ✅ Inserted 1 mempool snapshot into mempool_stats")
            print(f"      count={snapshot['count']}, vsize={snapshot['vsize']}, "
                  f"total_fee={snapshot['total_fee']} sats\n")

        # 3. Verify
        verify_data(conn)

    finally:
        conn.close()

    print("\n✅ Backfill complete!")


if __name__ == "__main__":
    main()
