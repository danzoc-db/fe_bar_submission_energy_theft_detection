"""TC-C: TTL cache tests.

Verifies the in-memory TTL cache used for SQL-heavy endpoints:
- Cache stores and retrieves values correctly
- Cache expires after TTL
- Default data must NEVER be cached
"""

import time as _time

import pytest


class TestCacheGetSet:
    """TC-C1: Basic cache get/set operations."""

    def test_cache_miss_returns_none(self):
        """MUST: Cache miss returns None."""
        from energy_theft_detection.backend.router import _cache, _cache_get

        _cache.pop("__test_miss__", None)
        assert _cache_get("__test_miss__") is None

    def test_cache_set_then_get(self):
        """MUST: Value is retrievable after set."""
        from energy_theft_detection.backend.router import _cache_get, _cache_set

        _cache_set("__test_hit__", {"answer": 42})
        result = _cache_get("__test_hit__")
        assert result == {"answer": 42}

    def test_cache_set_overwrites(self):
        """MUST: Second set overwrites first."""
        from energy_theft_detection.backend.router import _cache_get, _cache_set

        _cache_set("__test_overwrite__", "old")
        _cache_set("__test_overwrite__", "new")
        assert _cache_get("__test_overwrite__") == "new"


class TestCacheExpiry:
    """TC-C2: Cache entries expire after TTL."""

    def test_cache_expires_after_ttl(self):
        """MUST: Entries expire after _CACHE_TTL seconds."""
        from energy_theft_detection.backend.router import (
            _cache,
            _cache_get,
        )

        _cache["__test_expired__"] = (_time.monotonic() - 6000, "stale")
        assert _cache_get("__test_expired__") is None

    def test_cache_fresh_within_ttl(self):
        """MUST: Entries within TTL are returned."""
        from energy_theft_detection.backend.router import _cache_get, _cache_set

        _cache_set("__test_fresh__", "live")
        assert _cache_get("__test_fresh__") == "live"


class TestKPICacheGuard:
    """TC-C3: KPI endpoint never caches default data.

    This is a critical invariant. If the SQL client is unavailable, the
    endpoint returns hardcoded default values. Those values must NOT be
    cached — otherwise every subsequent request within the TTL window
    returns wrong data even after SQL becomes available.
    """

    def test_default_kpis_not_cached(self, client):
        """MUST: Default KPI data is NOT stored in cache."""
        from energy_theft_detection.backend.router import _cache, _cache_get

        _cache.pop("dashboard_kpis", None)

        r = client.get("/api/dashboard/kpis")
        assert r.status_code == 200
        assert _cache_get("dashboard_kpis") is None, (
            "_cache_set must be inside the SQL success path — "
            "default data was cached, which would serve wrong values"
        )

    def test_default_investigation_kpis_not_cached(self, client):
        """MUST: Default investigation KPI data is NOT cached."""
        from energy_theft_detection.backend.router import _cache, _cache_get

        _cache.pop("investigation_kpis", None)

        r = client.get("/api/investigation/kpis")
        assert r.status_code == 200
        assert _cache_get("investigation_kpis") is None

    def test_empty_heatmap_not_cached(self, client):
        """MUST: Empty heatmap default is NOT cached."""
        from energy_theft_detection.backend.router import _cache, _cache_get

        _cache.pop("dashboard_heatmap", None)

        r = client.get("/api/dashboard/heatmap")
        assert r.status_code == 200
        assert _cache_get("dashboard_heatmap") is None

    def test_empty_score_distribution_not_cached(self, client):
        """MUST: Empty score distribution default is NOT cached."""
        from energy_theft_detection.backend.router import _cache, _cache_get

        _cache.pop("dashboard_score_distribution", None)

        r = client.get("/api/dashboard/score-distribution")
        assert r.status_code == 200
        assert _cache_get("dashboard_score_distribution") is None
