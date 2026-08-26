"""TechnicalSnapshot repository."""
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.technical_snapshot import TechnicalSnapshot
from app.repositories.base import BaseRepository


class TechnicalSnapshotRepository(BaseRepository[TechnicalSnapshot]):
    def __init__(self, session: AsyncSession):
        super().__init__(TechnicalSnapshot, session)

    async def get_latest(self, symbol: str) -> Optional[TechnicalSnapshot]:
        stmt = select(TechnicalSnapshot).where(
            TechnicalSnapshot.symbol == symbol
        ).order_by(TechnicalSnapshot.trade_date.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_date(self, symbol: str, trade_date: str) -> Optional[TechnicalSnapshot]:
        return await self.find_one(symbol=symbol, trade_date=trade_date)

    async def upsert(self, data: dict) -> TechnicalSnapshot:
        """Insert or update by symbol+trade_date."""
        existing = await self.get_by_date(data["symbol"], data["trade_date"])
        if existing:
            return await self.update(existing.id, data)
        return await self.create(data)

    async def get_history(self, symbol: str, limit: int = 30) -> List[TechnicalSnapshot]:
        stmt = select(TechnicalSnapshot).where(
            TechnicalSnapshot.symbol == symbol
        ).order_by(TechnicalSnapshot.trade_date.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
