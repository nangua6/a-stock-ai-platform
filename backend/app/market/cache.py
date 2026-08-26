"""
In-memory TTL cache for market data.

Provides freshness tracking and stale-data detection.
No external dependencies (Redis interface reserved for future).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Generic, Optional, TypeVar

from app.market.base import DataFreshness

T = TypeVar("T")

# Default TTLs by data type (seconds)
DEFAULT_TTLS = {
    "quote": 10,            # Real-time quotes: 10s
    "quote_batch": 10,
    "kline_intraday": 30,   # Intraday klines: 30s
    "kline_daily": 300,     # Daily klines: 5min
    "kline_weekly": 1800,   # Weekly/monthly: 30min
    "financial": 3600,      # Financials: 1 hour
    "stock_list": 3600,     # Stock list: 1 hour
    "market_overview": 15,  # Market overview: 15s
    "money_flow": 30,       # Money flow: 30s
    "news": 60,             # News: 1min
    "announcements": 120,   # Announcements: 2min
}

# Stale threshold: how long past TTL before data is marked stale (multiplier)
STALE_MULTIPLIER = 3.0


@dataclass
class CacheEntry:
    """A single cached item with freshness metadata."""
    data: Any
    cached_at: float              # time.time() when cached
    ttl: float                    # TTL in seconds
    provider: str = ""            # Which provider produced this
    data_timestamp: str = ""      # Original data timestamp

    @property
    def age(self) -> float:
        """Age of this cache entry in seconds."""
        return time.time() - self.cached_at

    @property
    def is_expired(self) -> bool:
        return self.age > self.ttl

    @property
    def is_stale(self) -> bool:
        return self.age > self.ttl * STALE_MULTIPLIER

    @property
    def freshness(self) -> DataFreshness:
        if self.is_stale:
            return DataFreshness.UNAVAILABLE
        if self.is_expired:
            return DataFreshness.STALE
        return DataFreshness.FRESH

    @property
    def fetched_at_iso(self) -> str:
        return datetime.fromtimestamp(self.cached_at, tz=timezone.utc).isoformat()


class MarketDataCache:
    """
    In-memory cache with per-data-type TTL and freshness tracking.

    Thread-safe for asyncio (single-threaded event loop).
    """

    def __init__(self, ttls: Optional[Dict[str, float]] = None):
        self._store: Dict[str, CacheEntry] = {}
        self._ttls = {**DEFAULT_TTLS, **(ttls or {})}
        self._hits: int = 0
        self._misses: int = 0

    def _cache_key(self, data_type: str, symbol: str = "") -> str:
        if symbol:
            return f"{data_type}:{symbol}"
        return data_type

    def get(self, data_type: str, symbol: str = "") -> Optional[CacheEntry]:
        """Get a cache entry if it exists and is not fully stale."""
        key = self._cache_key(data_type, symbol)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_stale:
            # Remove fully stale entries
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry

    def put(
        self,
        data_type: str,
        data: Any,
        symbol: str = "",
        provider: str = "",
        data_timestamp: str = "",
        ttl_override: Optional[float] = None,
    ) -> None:
        """Store data in cache."""
        key = self._cache_key(data_type, symbol)
        ttl = ttl_override or self._ttls.get(data_type, 60)
        self._store[key] = CacheEntry(
            data=data,
            cached_at=time.time(),
            ttl=ttl,
            provider=provider,
            data_timestamp=data_timestamp,
        )

    def invalidate(self, data_type: str, symbol: str = "") -> None:
        """Remove a specific cache entry."""
        key = self._cache_key(data_type, symbol)
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all cached data."""
        self._store.clear()

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "entries": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
        }
