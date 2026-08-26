"""AnalysisSnapshot repository."""
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_snapshot import AnalysisSnapshot
from app.repositories.base import BaseRepository


class AnalysisSnapshotRepository(BaseRepository[AnalysisSnapshot]):
    def __init__(self, session: AsyncSession):
        super().__init__(AnalysisSnapshot, session)

    async def get_latest(self, symbol: str) -> Optional[AnalysisSnapshot]:
        stmt = select(AnalysisSnapshot).where(
            AnalysisSnapshot.symbol == symbol
        ).order_by(AnalysisSnapshot.trade_date.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_date(self, symbol: str, trade_date: str) -> Optional[AnalysisSnapshot]:
        return await self.find_one(symbol=symbol, trade_date=trade_date)

    async def upsert(self, data: dict) -> AnalysisSnapshot:
        """Insert or update by symbol+trade_date."""
        existing = await self.get_by_date(data["symbol"], data["trade_date"])
        if existing:
            return await self.update(existing.id, data)
        return await self.create(data)

    async def get_by_recommendation(self, recommendation: str, limit: int = 50) -> List[AnalysisSnapshot]:
        return await self.find_many(
            recommendation=recommendation, limit=limit,
            order_by="trade_date", descending=True,
        )
