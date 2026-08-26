"""Signal repository."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import Signal
from app.repositories.base import BaseRepository


class SignalRepository(BaseRepository[Signal]):
    def __init__(self, session: AsyncSession):
        super().__init__(Signal, session)

    async def get_active_signals(
        self, account_id: Optional[uuid.UUID] = None
    ) -> List[Signal]:
        filters = {"status": "ACTIVE"}
        if account_id:
            filters["account_id"] = account_id
        return await self.find_many(
            order_by="signal_time", descending=True, **filters
        )

    async def get_by_symbol(self, symbol: str, limit: int = 20) -> List[Signal]:
        return await self.find_many(
            symbol=symbol, order_by="signal_time", descending=True, limit=limit
        )

    async def get_by_strategy(self, strategy_name: str, limit: int = 50) -> List[Signal]:
        return await self.find_many(
            strategy_name=strategy_name, order_by="signal_time", descending=True, limit=limit
        )

    async def get_by_agent(self, agent_name: str, limit: int = 50) -> List[Signal]:
        return await self.find_many(
            agent_name=agent_name, order_by="signal_time", descending=True, limit=limit
        )

    async def expire_old_signals(self, max_age_hours: int = 24) -> int:
        """Mark signals older than max_age_hours as EXPIRED."""
        cutoff = datetime.utcnow().replace(hour=datetime.utcnow().hour - max_age_hours)
        stmt = select(Signal).where(
            and_(Signal.status == "ACTIVE", Signal.signal_time < cutoff)
        )
        result = await self.session.execute(stmt)
        signals = result.scalars().all()
        count = 0
        for sig in signals:
            await self.update(sig.id, {"status": "EXPIRED"})
            count += 1
        return count

    async def mark_executed(self, signal_id: uuid.UUID) -> Optional[Signal]:
        return await self.update(signal_id, {"status": "EXECUTED"})
