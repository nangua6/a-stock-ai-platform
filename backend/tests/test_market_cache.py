"""Tests for MarketDataCache."""
import time
import pytest
from app.market.cache import MarketDataCache, CacheEntry
from app.market.base import DataFreshness


class TestCacheEntry:
    def test_fresh_entry(self):
        entry = CacheEntry(data="test", cached_at=time.time(), ttl=60)
        assert entry.freshness == DataFreshness.FRESH
        assert not entry.is_expired
        assert not entry.is_stale

    def test_expired_entry(self):
        entry = CacheEntry(data="test", cached_at=time.time() - 120, ttl=60)
        assert entry.is_expired
        assert entry.freshness == DataFreshness.STALE

    def test_stale_entry(self):
        # 3x TTL = stale/unavailable
        entry = CacheEntry(data="test", cached_at=time.time() - 200, ttl=60)
        assert entry.is_stale
        assert entry.freshness == DataFreshness.UNAVAILABLE


class TestMarketDataCache:
    def setup_method(self):
        self.cache = MarketDataCache()

    def test_put_and_get(self):
        self.cache.put("quote", {"price": 100}, symbol="TEST.SH", provider="mock")
        entry = self.cache.get("quote", "TEST.SH")
        assert entry is not None
        assert entry.data == {"price": 100}
        assert entry.provider == "mock"

    def test_cache_miss(self):
        entry = self.cache.get("quote", "MISSING.SH")
        assert entry is None

    def test_invalidate(self):
        self.cache.put("quote", {"price": 100}, symbol="TEST.SH")
        self.cache.invalidate("quote", "TEST.SH")
        assert self.cache.get("quote", "TEST.SH") is None

    def test_clear(self):
        self.cache.put("quote", {"price": 100}, symbol="A.SH")
        self.cache.put("quote", {"price": 200}, symbol="B.SH")
        self.cache.clear()
        assert self.cache.get("quote", "A.SH") is None
        assert self.cache.get("quote", "B.SH") is None

    def test_stats(self):
        self.cache.put("quote", {"price": 100}, symbol="A.SH")
        self.cache.get("quote", "A.SH")  # hit
        self.cache.get("quote", "B.SH")  # miss
        stats = self.cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["entries"] == 1

    def test_custom_ttl(self, monkeypatch):
        """Expired-but-not-stale entries should still be retrievable."""
        base_time = 1000000.0
        monkeypatch.setattr(time, "time", lambda: base_time)
        self.cache.put("quote", {"price": 100}, symbol="A.SH", ttl_override=10.0)

        # Advance past TTL (10s) but before stale threshold (30s = 3x TTL)
        monkeypatch.setattr(time, "time", lambda: base_time + 15.0)
        entry = self.cache.get("quote", "A.SH")
        assert entry is not None  # Still available as stale
        assert entry.freshness == DataFreshness.STALE

    def test_custom_ttl_stale_removes(self, monkeypatch):
        """Entries past 3x TTL should be removed."""
        base_time = 1000000.0
        monkeypatch.setattr(time, "time", lambda: base_time)
        self.cache.put("quote", {"price": 100}, symbol="A.SH", ttl_override=10.0)

        # Advance past 3x TTL (30s) → UNAVAILABLE → removed
        monkeypatch.setattr(time, "time", lambda: base_time + 35.0)
        entry = self.cache.get("quote", "A.SH")
        assert entry is None
