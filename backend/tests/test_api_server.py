"""Tests for the FastAPI data layer (CQRS: Redis read model).

Uses fakeredis to simulate the Redis read layer.
Tests cover both happy path (data in Redis) and cache miss (empty Redis).
"""

import json
from datetime import datetime, timezone

import fakeredis
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


# =============================================================================
# Test data (mirrors what _project_to_redis() writes from DuckDB)
# =============================================================================

SEED_MEMPOOL_STATS = {
    "mempool_size": 38446,
    "mempool_bytes": 19529746,
    "total_fee_sats": 3449075,
    "median_fee": 18.3,
    "blocks_to_clear": 2,
    "delta_size_pct": -5.2,
    "delta_fee_pct": 12.1,
}

SEED_FEE_DISTRIBUTION = {
    "bands": [
        {"range": "1-5", "count": 1200, "pct": 15.5},
        {"range": "5-10", "count": 2400, "pct": 31.0},
        {"range": "10-15", "count": 1800, "pct": 23.2},
        {"range": "15-20", "count": 900, "pct": 11.6},
        {"range": "20-30", "count": 700, "pct": 9.0},
        {"range": "30-50", "count": 500, "pct": 6.5},
        {"range": "50+", "count": 250, "pct": 3.2},
    ],
    "total_txs": 7750,
    "peak_band": "5-10",
}

SEED_RECENT_BLOCKS = {
    "blocks": [
        {
            "height": 881247,
            "timestamp": "2026-02-21T22:00:00",
            "tx_count": 3842,
            "size_bytes": 1980000,
            "median_fee": 18.3,
            "total_fees_sats": 18470000,
            "fee_range": [1.0, 2.0, 5.0, 12.0, 20.0, 35.0, 178.0],
            "pool_name": "Foundry USA",
        },
        {
            "height": 881246,
            "timestamp": "2026-02-21T21:50:00",
            "tx_count": 3742,
            "size_bytes": 1970000,
            "median_fee": 17.3,
            "total_fees_sats": 17470000,
            "fee_range": [1.0, 2.0, 5.0, 11.0, 19.0, 34.0, 165.0],
            "pool_name": "AntPool",
        },
    ],
    "latest_height": 881247,
}

SEED_WATCHLIST = {
    "advisories": [
        {
            "txid": "a" * 64,
            "role": "SENDER",
            "status": "Stuck",
            "current_fee_rate": 8.0,
            "action": "RBF to 18.3 sat/vB",
            "action_type": "RBF",
            "cost_sats": 4124,
        },
        {
            "txid": "b" * 64,
            "role": "RECEIVER",
            "status": "Stuck",
            "current_fee_rate": 4.0,
            "action": "CPFP Child: 18.3 sat/vB",
            "action_type": "CPFP",
            "cost_sats": 2580,
        },
        {
            "txid": "c" * 64,
            "role": "SENDER",
            "status": "CONFIRMED",
            "current_fee_rate": 15.0,
            "action": "No action needed",
            "action_type": "None",
            "cost_sats": None,
        },
    ],
    "stuck_count": 2,
    "total_count": 3,
}

SEED_ORCHESTRATOR_STATUS = {
    "strategy_mode": "PATIENT",
    "current_median_fee": 18.3,
    "historical_median_fee": 12.5,
    "ema_fee": 14.7,
    "ema_trend": "RISING",
    "fee_premium_pct": 46.4,
    "traffic_level": "NORMAL",
    "latest_block_height": 881247,
}


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def fake_redis():
    """Create a fakeredis instance pre-populated with dashboard data."""
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server, decode_responses=True)
    r.set("dashboard:mempool_stats", json.dumps(SEED_MEMPOOL_STATS))
    r.set("dashboard:fee_distribution", json.dumps(SEED_FEE_DISTRIBUTION))
    r.set("dashboard:recent_blocks", json.dumps(SEED_RECENT_BLOCKS))
    r.set("dashboard:watchlist", json.dumps(SEED_WATCHLIST))
    r.set("dashboard:orchestrator_status", json.dumps(SEED_ORCHESTRATOR_STATUS))
    yield r
    r.flushall()


@pytest.fixture()
def empty_redis():
    """Create an empty fakeredis instance (cache miss scenario)."""
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server, decode_responses=True)
    yield r
    r.flushall()


@pytest.fixture()
def client(fake_redis):
    """FastAPI test client with mocked Redis (populated)."""
    import src.api.main as api_main

    api_main._redis_client = fake_redis
    with TestClient(api_main.app) as c:
        yield c
    api_main._redis_client = None


@pytest.fixture()
def empty_client(empty_redis):
    """FastAPI test client with empty Redis (cache miss)."""
    import src.api.main as api_main

    api_main._redis_client = empty_redis
    with TestClient(api_main.app) as c:
        yield c
    api_main._redis_client = None


# =============================================================================
# Tests: /api/mempool/stats
# =============================================================================

class TestMempoolStats:
    """Tests for the KPI cards endpoint."""

    def test_returns_current_stats(self, client):
        response = client.get("/api/mempool/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["mempool_size"] == 38446
        assert data["mempool_bytes"] == 19529746
        assert data["total_fee_sats"] == 3449075
        assert data["median_fee"] == 18.3
        assert data["blocks_to_clear"] == 2

    def test_deltas_present_when_data_exists(self, client):
        response = client.get("/api/mempool/stats")
        data = response.json()
        assert data["delta_size_pct"] == -5.2
        assert data["delta_fee_pct"] == 12.1

    def test_cache_miss_returns_empty_state(self, empty_client):
        response = empty_client.get("/api/mempool/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["mempool_size"] == 0
        assert data["median_fee"] == 0.0
        assert data["delta_size_pct"] is None
        assert data["delta_fee_pct"] is None


# =============================================================================
# Tests: /api/mempool/fee-distribution
# =============================================================================

class TestFeeDistribution:
    """Tests for the fee histogram endpoint."""

    def test_returns_fee_bands(self, client):
        response = client.get("/api/mempool/fee-distribution")
        assert response.status_code == 200

        data = response.json()
        assert len(data["bands"]) == 7
        assert data["total_txs"] == 7750
        assert data["peak_band"] == "5-10"

    def test_band_percentages_sum_to_100(self, client):
        response = client.get("/api/mempool/fee-distribution")
        data = response.json()
        total_pct = sum(b["pct"] for b in data["bands"])
        assert 99.5 <= total_pct <= 100.5

    def test_cache_miss_returns_empty_bands(self, empty_client):
        response = empty_client.get("/api/mempool/fee-distribution")
        assert response.status_code == 200

        data = response.json()
        assert data["bands"] == []
        assert data["total_txs"] == 0
        assert data["peak_band"] == "N/A"


# =============================================================================
# Tests: /api/blocks/recent
# =============================================================================

class TestRecentBlocks:
    """Tests for the blocks table endpoint."""

    def test_returns_blocks(self, client):
        response = client.get("/api/blocks/recent")
        assert response.status_code == 200

        data = response.json()
        assert len(data["blocks"]) == 2
        assert data["latest_height"] == 881247

    def test_blocks_ordered_by_height_desc(self, client):
        response = client.get("/api/blocks/recent")
        data = response.json()
        heights = [b["height"] for b in data["blocks"]]
        assert heights == sorted(heights, reverse=True)

    def test_limit_parameter_slices_blocks(self, client):
        response = client.get("/api/blocks/recent?limit=1")
        data = response.json()
        assert len(data["blocks"]) == 1

    def test_block_has_required_fields(self, client):
        response = client.get("/api/blocks/recent?limit=1")
        block = response.json()["blocks"][0]
        assert "height" in block
        assert "timestamp" in block
        assert "tx_count" in block
        assert "size_bytes" in block
        assert "median_fee" in block
        assert "total_fees_sats" in block
        assert "fee_range" in block
        assert "pool_name" in block

    def test_cache_miss_returns_empty_blocks(self, empty_client):
        response = empty_client.get("/api/blocks/recent")
        assert response.status_code == 200

        data = response.json()
        assert data["blocks"] == []
        assert data["latest_height"] is None


# =============================================================================
# Tests: /api/watchlist
# =============================================================================

class TestWatchlist:
    """Tests for the advisors panel endpoint."""

    def test_returns_advisories(self, client):
        response = client.get("/api/watchlist")
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 3
        assert data["stuck_count"] == 2

    def test_confirmed_tx_has_no_action(self, client):
        response = client.get("/api/watchlist")
        data = response.json()
        confirmed = [a for a in data["advisories"] if a["status"] == "CONFIRMED"]
        assert len(confirmed) == 1
        assert confirmed[0]["action_type"] == "None"
        assert confirmed[0]["action"] == "No action needed"

    def test_stuck_sender_gets_rbf_advice(self, client):
        response = client.get("/api/watchlist")
        data = response.json()
        sender = [a for a in data["advisories"] if a["txid"] == "a" * 64]
        assert len(sender) == 1
        assert sender[0]["action_type"] == "RBF"

    def test_stuck_receiver_gets_cpfp_advice(self, client):
        response = client.get("/api/watchlist")
        data = response.json()
        receiver = [a for a in data["advisories"] if a["txid"] == "b" * 64]
        assert len(receiver) == 1
        assert receiver[0]["action_type"] == "CPFP"

    def test_cache_miss_returns_empty_watchlist(self, empty_client):
        response = empty_client.get("/api/watchlist")
        assert response.status_code == 200

        data = response.json()
        assert data["advisories"] == []
        assert data["stuck_count"] == 0
        assert data["total_count"] == 0


# =============================================================================
# Tests: /api/orchestrator/status
# =============================================================================

class TestOrchestratorStatus:
    """Tests for the strategy engine status endpoint."""

    def test_returns_status(self, client):
        response = client.get("/api/orchestrator/status")
        assert response.status_code == 200

        data = response.json()
        assert data["strategy_mode"] == "PATIENT"
        assert data["current_median_fee"] == 18.3
        assert data["ema_trend"] == "RISING"
        assert data["traffic_level"] == "NORMAL"
        assert data["latest_block_height"] == 881247

    def test_fee_premium_is_calculated(self, client):
        response = client.get("/api/orchestrator/status")
        data = response.json()
        assert data["fee_premium_pct"] == 46.4

    def test_cache_miss_returns_default_status(self, empty_client):
        response = empty_client.get("/api/orchestrator/status")
        assert response.status_code == 200

        data = response.json()
        assert data["strategy_mode"] == "PATIENT"
        assert data["current_median_fee"] == 0.0
        assert data["ema_trend"] == "STABLE"
        assert data["traffic_level"] == "LOW"
        assert data["latest_block_height"] is None


# =============================================================================
# Tests: CORS
# =============================================================================

class TestCORS:
    """Verify CORS middleware allows localhost:3000."""

    def test_cors_allowed_origin(self, client):
        response = client.get(
            "/api/mempool/stats",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_disallowed_origin(self, client):
        response = client.get(
            "/api/mempool/stats",
            headers={"Origin": "http://evil.com"},
        )
        assert response.headers.get("access-control-allow-origin") is None
