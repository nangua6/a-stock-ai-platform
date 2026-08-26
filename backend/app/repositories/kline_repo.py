"""Kline (OHLCV) repository."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kline import Kline
from app.repositories.base import BaseRepository


class KlineRepository(BaseRepository[Kline]):
    def __init__(self, session: AsyncSession):
        super().__init__(Kline, session)

    async def get_by_symbol(
        self,
        symbol: str,
        timeframe: str = "D",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Kline]:
        """Get kline data for a symbol with optional date range."""
        stmt = select(Kline).where(
            and_(Kline.symbol == symbol, Kline.timeframe == timeframe)
        )
        if start_date:
            stmt = stmt.where(Kline.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(Kline.trade_date <= end_date)
        stmt = stmt.order_by(Kline.trade_date.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest(self, symbol: str, timeframe: str = "D") -> Optional[Kline]:
        """Get the most recent kline bar for a symbol."""
        stmt = select(Kline).where(
            and_(Kline.symbol == symbol, Kline.timeframe == timeframe)
        ).order_by(Kline.trade_date.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_closes(self, symbol: str, timeframe: str = "D", limit: int = 100) -> List[float]:
        """Get just the close prices for indicator calculation."""
        klines = await self.get_by_symbol(symbol, timeframe, limit=limit)
        return [k.close for k in klines]

    async def bulk_upsert(self, klines: List[dict]) -> int:
        """Insert or update kline records (upsert by symbol+trade_date+timeframe)."""
        count = 0
        for data in klines:
            existing = await self.find_one(
                symbol=data["symbol"],
                trade_date=data["trade_date"],
                timeframe=data.get("timeframe", "D"),
            )
            if existing:
                await self.update(existing.id, data)
            else:
                await self.create(data)
            count += 1
        return count

    async def get_date_range(self, symbol: str, timeframe: str = "D") -> dict:
        """Get the available date range for a symbol."""
        stmt = select(
            func.min(Kline.trade_date),
            func.max(Kline.trade_date),
            func.count(),
        ).where(and_(Kline.symbol == symbol, Kline.timeframe == timeframe))
        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "min_date": row[0],
            "max_date": row[1],
            "count": row[2],
        }
