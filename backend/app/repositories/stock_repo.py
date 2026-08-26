"""Stock repository."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.repositories.base import BaseRepository


class StockRepository(BaseRepository[Stock]):
    def __init__(self, session: AsyncSession):
        super().__init__(Stock, session)

    async def get_by_symbol(self, symbol: str) -> Optional[Stock]:
        return await self.find_one(symbol=symbol)

    async def get_by_market(self, market: str) -> List[Stock]:
        return await self.find_many(market=market, is_active=True)

    async def get_by_industry(self, industry: str) -> List[Stock]:
        return await self.find_many(industry=industry, is_active=True)

    async def get_st_stocks(self) -> List[Stock]:
        return await self.find_many(is_st=True, is_active=True)

    async def get_active_stocks(self) -> List[Stock]:
        return await self.find_many(is_active=True, limit=10000)

    async def search_by_name(self, name: str) -> List[Stock]:
        """Search stocks by name (partial match)."""
        stmt = select(Stock).where(
            Stock.name.ilike(f"%{name}%"),
            Stock.is_active == True,
        ).limit(20)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_quote(
        self, symbol: str, price: float, volume: int, amount: float, timestamp: str
    ) -> Optional[Stock]:
        stock = await self.get_by_symbol(symbol)
        if stock:
            return await self.update(stock.id, {
                "latest_price": price,
                "latest_volume": volume,
                "latest_amount": amount,
                "latest_update": timestamp,
            })
        return None

    async def bulk_create(self, stocks: List[dict]) -> int:
        """Bulk create stock records. Returns count created."""
        count = 0
        for data in stocks:
            existing = await self.get_by_symbol(data.get("symbol", ""))
            if not existing:
                await self.create(data)
                count += 1
        return count
