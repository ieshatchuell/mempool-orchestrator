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
    "delta_total_fee_pct": 8.4,
    "delta_blocks_pct": -3.1,
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
            "status": "Stuck",
            "current_fee_rate": 8.0,
            "rbf": {"action": "RBF to 18.3 sat/vB", "cost_sats": 4124},
            "cpfp": {"action": "CPFP Child: 18.3 sat/vB", "cost_sats": 2580},
        },
        {
            "txid": "b" * 64,
            "status": "Pending",
            "current_fee_rate": 20.0,
            "rbf": None,
            "cpfp": None,
        },
        {
            "txid": "c" * 64,
            "status": "Confirmed",
            "current_fee_rate": 15.0,
            "rbf": None,
            "cpfp": None,
        },
    ],
    "stuck_count": 1,
    "total_count": 3,
}

SEED_ORCHESTRATOR_STATUS = {
    "current_median_fee": 18.3,
    "historical_median_fee": 12.5,
    "ema_fee": 14.7,
    "ema_trend": "RISING",
    "fee_premium_pct": 46.4,
    "traffic_level": "NORMAL",
    "latest_block_height": 881247,
    "patient": {
        "action": "WAIT",
        "recommended_fee": 13,
        "confidence": 0.8,
    },
    "reliable": {
        "action": "BROADCAST",
        "recommended_fee": 15,
        "confidence": 0.8,
    },
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
        assert data["delta_total_fee_pct"] == 8.4
        assert data["delta_blocks_pct"] == -3.1

    def test_cache_miss_returns_empty_state(self, empty_client):
        response = empty_client.get("/api/mempool/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["mempool_size"] == 0
        assert data["median_fee"] == 0.0
        assert data["delta_size_pct"] is None
        assert data["delta_fee_pct"] is None
        assert data["delta_total_fee_pct"] is None
        assert data["delta_blocks_pct"] is None


# =============================================================================
# Tests: /api/mempool/fee-distribution (deprecated — should 404/405)
# =============================================================================

class TestFeeDistributionDeprecated:
    """Verify fee-distribution endpoint is removed."""

    def test_fee_distribution_endpoint_gone(self, client):
        response = client.get("/api/mempool/fee-distribution")
        # 404 (no route) or 405 (method not allowed) — both valid
        assert response.status_code in (404, 405)


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
        assert data["stuck_count"] == 1

    def test_stuck_tx_has_dual_advisors(self, client):
        """Stuck txs should have BOTH rbf and cpfp advice."""
        response = client.get("/api/watchlist")
        data = response.json()
        stuck = [a for a in data["advisories"] if a["status"] == "Stuck"]
        assert len(stuck) == 1
        assert stuck[0]["rbf"] is not None
        assert stuck[0]["cpfp"] is not None
        assert stuck[0]["rbf"]["cost_sats"] is not None
        assert stuck[0]["cpfp"]["cost_sats"] is not None

    def test_confirmed_tx_has_no_advisors(self, client):
        response = client.get("/api/watchlist")
        data = response.json()
        confirmed = [a for a in data["advisories"] if a["status"] == "Confirmed"]
        assert len(confirmed) == 1
        assert confirmed[0]["rbf"] is None
        assert confirmed[0]["cpfp"] is None

    def test_pending_tx_has_no_advisors(self, client):
        """Pending (not stuck) txs should have null advisors."""
        response = client.get("/api/watchlist")
        data = response.json()
        pending = [a for a in data["advisories"] if a["status"] == "Pending"]
        assert len(pending) == 1
        assert pending[0]["rbf"] is None
        assert pending[0]["cpfp"] is None

    def test_no_role_field(self, client):
        """Advisories should NOT have a 'role' field."""
        response = client.get("/api/watchlist")
        data = response.json()
        for advisory in data["advisories"]:
            assert "role" not in advisory

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
    """Tests for the dual-strategy engine status endpoint."""

    def test_returns_status(self, client):
        response = client.get("/api/orchestrator/status")
        assert response.status_code == 200

        data = response.json()
        assert data["current_median_fee"] == 18.3
        assert data["ema_trend"] == "RISING"
        assert data["traffic_level"] == "NORMAL"
        assert data["latest_block_height"] == 881247

    def test_dual_strategy_present(self, client):
        """Response must have both patient and reliable results."""
        response = client.get("/api/orchestrator/status")
        data = response.json()
        assert "patient" in data
        assert "reliable" in data
        assert data["patient"]["action"] in ("BROADCAST", "WAIT")
        assert data["reliable"]["action"] in ("BROADCAST", "WAIT")
        assert data["patient"]["recommended_fee"] > 0
        assert data["reliable"]["recommended_fee"] > 0

    def test_no_strategy_mode_field(self, client):
        """Response should NOT have a top-level 'strategy_mode' field."""
        response = client.get("/api/orchestrator/status")
        data = response.json()
        assert "strategy_mode" not in data

    def test_cache_miss_returns_default_status(self, empty_client):
        response = empty_client.get("/api/orchestrator/status")
        assert response.status_code == 200

        data = response.json()
        assert data["current_median_fee"] == 0.0
        assert data["ema_trend"] == "STABLE"
        assert data["traffic_level"] == "LOW"
        assert data["latest_block_height"] is None
        assert data["patient"]["action"] == "WAIT"
        assert data["reliable"]["action"] == "BROADCAST"


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
