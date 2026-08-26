"""
Market data service – bridges ProviderManager with the database.

Responsibilities:
1. Fetch data from provider chain (AkShare → Mock fallback)
2. Persist to database (stocks, klines)
3. Read from DB when provider is unavailable (stale-while-revalidate)
4. Expose provider health and cache status
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_data_logger
from app.market.base import DataAvailability, DataFreshness, MarketDataProvider
from app.market.provider_manager import ProviderManager
from app.market.cache import MarketDataCache
from app.repositories.factory import RepositoryFactory

logger = get_data_logger()

# How old DB data can be before we re-fetch (seconds)
DB_STALE_THRESHOLD = 300  # 5 minutes


class MarketDataService:
    """Bridges market data providers with persistent storage."""

    def __init__(self, session: AsyncSession, provider: MarketDataProvider):
        self.repos = RepositoryFactory(session)
        self.provider = provider

    @property
    def provider_manager(self) -> Optional[ProviderManager]:
        """Get the underlying ProviderManager if available."""
        return self.provider if isinstance(self.provider, ProviderManager) else None

    async def sync_stock_list(self, market: Optional[str] = None) -> int:
        """Fetch and persist the full stock list from provider."""
        stocks = await self.provider.get_stock_list(market)
        if not stocks:
            logger.warning("sync_stock_list_empty", market=market)
            return 0
        count = await self.repos.stocks.bulk_create([
            {
                "symbol": s["symbol"],
                "name": s["name"],
                "market": s.get("market", s["symbol"].split(".")[-1]),
                "industry": s.get("industry", ""),
                "is_active": True,
            }
            for s in stocks
        ])
        logger.info("stock_list_synced", count=count, provider=self.provider.name)
        return count

    async def sync_klines(
        self,
        symbol: str,
        timeframe: str = "D",
        limit: int = 200,
    ) -> int:
        """Fetch and persist kline data for a symbol."""
        klines = await self.provider.get_kline(symbol, timeframe=timeframe, limit=limit)
        if not klines:
            logger.warning("sync_klines_empty", symbol=symbol)
            return 0
        data = [
            {
                "symbol": k.symbol,
                "trade_date": k.trade_date,
                "timeframe": k.timeframe,
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
                "amount": k.amount,
                "change_pct": k.change_pct,
                "data_source": k.data_source,
                "available_time": k.available_time,
            }
            for k in klines
        ]
        count = await self.repos.klines.bulk_upsert(data)
        logger.info("klines_synced", symbol=symbol, count=count, timeframe=timeframe)
        return count

    async def update_quote_snapshot(self, symbol: str) -> dict:
        """Fetch and store latest quote for a symbol."""
        quote = await self.provider.get_realtime_quote(symbol)
        stock = await self.repos.stocks.update_quote(
            symbol=symbol,
            price=quote.price,
            volume=quote.volume,
            amount=quote.amount,
            timestamp=quote.timestamp,
        )
        if stock:
            logger.info("quote_snapshot_updated", symbol=symbol, price=quote.price,
                       provider=quote.data_source)
        else:
            logger.warning("quote_snapshot_stock_not_found", symbol=symbol)
        return quote.__dict__

    async def get_historical_closes(
        self, symbol: str, limit: int = 100, prefer_db: bool = True,
    ) -> List[float]:
        """Get close prices, preferring DB (fast) then falling back to provider."""
        if prefer_db:
            closes = await self.repos.klines.get_closes(symbol, limit=limit)
            if closes and len(closes) >= min(limit, 5):
                logger.info("closes_from_db", symbol=symbol, count=len(closes))
                return closes

        # DB empty or stale – fetch from provider and persist
        synced = await self.sync_klines(symbol, limit=limit)
        if synced > 0:
            closes = await self.repos.klines.get_closes(symbol, limit=limit)
            if closes:
                return closes

        # Last resort: return what we have from DB (may be stale)
        return await self.repos.klines.get_closes(symbol, limit=limit)

    async def get_market_overview(self) -> dict:
        """Get market overview from provider (not persisted – always fresh)."""
        return await self.provider.get_market_overview()

    async def get_data_status(self) -> dict:
        """Get comprehensive data status: providers, cache, DB stats."""
        status: Dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Provider status
        pm = self.provider_manager
        if pm:
            status["providers"] = pm.get_provider_status()
            status["primary_provider"] = pm.primary_provider
        else:
            status["providers"] = [{"provider": self.provider.name, "note": "single provider"}]

        # DB stats
        try:
            stock_count = await self.repos.stocks.count(is_active=True)
            status["db"] = {"active_stocks": stock_count}
        except Exception as e:
            status["db"] = {"error": str(e)[:100]}

        return status

    async def sync_full(self, symbol: str) -> dict:
        """Full sync for a symbol: quote + klines. Returns sync result."""
        result = {"symbol": symbol, "synced": {}, "errors": {}}

        # Sync quote
        try:
            quote_data = await self.update_quote_snapshot(symbol)
            result["synced"]["quote"] = {
                "price": quote_data.get("price"),
                "data_source": quote_data.get("data_source"),
            }
        except Exception as e:
            result["errors"]["quote"] = str(e)[:200]
            logger.warning("sync_quote_failed", symbol=symbol, error=str(e)[:200])

        # Sync klines
        try:
            count = await self.sync_klines(symbol, limit=200)
            result["synced"]["klines"] = {"count": count}
        except Exception as e:
            result["errors"]["klines"] = str(e)[:200]
            logger.warning("sync_klines_failed", symbol=symbol, error=str(e)[:200])

        return result
