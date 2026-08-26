"""Trade (fill) repository."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Trade
from app.repositories.base import BaseRepository


class TradeRepository(BaseRepository[Trade]):
    def __init__(self, session: AsyncSession):
        super().__init__(Trade, session)

    async def get_by_account(
        self, account_id: uuid.UUID, limit: int = 100
    ) -> List[Trade]:
        return await self.find_many(
            account_id=account_id,
            order_by="trade_time",
            descending=True,
            limit=limit,
        )

    async def get_by_order(self, order_id: uuid.UUID) -> List[Trade]:
        return await self.find_many(order_id=order_id)

    async def get_by_symbol(
        self, account_id: uuid.UUID, symbol: str
    ) -> List[Trade]:
        return await self.find_many(
            account_id=account_id, symbol=symbol,
            order_by="trade_time", descending=True,
        )

    async def get_daily_trades(self, account_id: uuid.UUID, trade_date: str) -> List[Trade]:
        """Get all trades for a specific date."""
        stmt = select(Trade).where(
            and_(
                Trade.account_id == account_id,
                func.date(Trade.trade_time) == trade_date,
            )
        ).order_by(Trade.trade_time.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_commission(self, account_id: uuid.UUID) -> float:
        """Get total commission paid for an account."""
        stmt = select(func.sum(Trade.commission)).where(
            Trade.account_id == account_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0.0

    async def get_total_amount(self, account_id: uuid.UUID) -> float:
        """Get total traded amount for an account."""
        stmt = select(func.sum(Trade.amount)).where(
            Trade.account_id == account_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0.0

    async def get_trade_count(self, account_id: uuid.UUID) -> int:
        return await self.count(account_id=account_id)
