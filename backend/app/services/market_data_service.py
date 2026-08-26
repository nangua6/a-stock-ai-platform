"""
Market data service – bridges MarketDataProvider with the database.

Responsibilities:
1. Fetch data from provider (Tushare/AkShare/etc.)
2. Persist to database (stocks, klines, financials)
3. Update cache (Redis)
4. Provide data to strategies and agents from DB when provider is unavailable
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_data_logger
from app.market.base import MarketDataProvider
from app.repositories.factory import RepositoryFactory

logger = get_data_logger()


class MarketDataService:
    """Bridges market data providers with persistent storage."""

    def __init__(self, session: AsyncSession, provider: MarketDataProvider):
        self.repos = RepositoryFactory(session)
        self.provider = provider

    async def sync_stock_list(self, market: Optional[str] = None) -> int:
        """Fetch and persist the full stock list from provider."""
        stocks = await self.provider.get_stock_list(market)
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
        logger.info("Stock list synced", count=count, provider=self.provider.name)
        return count

    async def sync_klines(
        self,
        symbol: str,
        timeframe: str = "D",
        limit: int = 200,
    ) -> int:
        """Fetch and persist kline data for a symbol."""
        klines = await self.provider.get_kline(symbol, timeframe=timeframe, limit=limit)
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
        logger.info("Klines synced", symbol=symbol, count=count)
        return count

    async def update_quote_snapshot(self, symbol: str) -> dict:
        """Fetch and store latest quote for a symbol."""
        quote = await self.provider.get_realtime_quote(symbol)
        await self.repos.stocks.update_quote(
            symbol=symbol,
            price=quote.price,
            volume=quote.volume,
            amount=quote.amount,
            timestamp=quote.timestamp,
        )
        return quote.__dict__

    async def get_historical_closes(self, symbol: str, limit: int = 100) -> List[float]:
        """Get close prices from DB, falling back to provider if needed."""
        closes = await self.repos.klines.get_closes(symbol, limit=limit)
        if not closes:
            # DB empty – fetch from provider and persist
            await self.sync_klines(symbol, limit=limit)
            closes = await self.repos.klines.get_closes(symbol, limit=limit)
        return closes

    async def get_market_overview(self) -> dict:
        """Get market overview from provider (not persisted – always fresh)."""
        return await self.provider.get_market_overview()
