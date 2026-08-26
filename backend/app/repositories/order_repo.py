"""Order repository with trade-specific queries."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_by_client_order_id(self, client_order_id: str) -> Optional[Order]:
        return await self.find_one(client_order_id=client_order_id)

    async def get_by_account(
        self, account_id: uuid.UUID, status: Optional[str] = None, limit: int = 100
    ) -> List[Order]:
        filters = {"account_id": account_id}
        if status:
            filters["status"] = status
        return await self.find_many(order_by="created_at", descending=True, limit=limit, **filters)

    async def get_pending_orders(self, account_id: uuid.UUID) -> List[Order]:
        return await self.find_many(
            account_id=account_id,
            status=OrderStatus.PENDING.value,
        )

    async def get_pending_confirm_orders(self, account_id: uuid.UUID) -> List[Order]:
        return await self.find_many(
            account_id=account_id,
            status=OrderStatus.PENDING_CONFIRM.value,
        )

    async def get_active_orders(self, account_id: uuid.UUID) -> List[Order]:
        """Get all non-terminal orders (pending, submitted, partial fill)."""
        stmt = select(Order).where(
            and_(
                Order.account_id == account_id,
                Order.status.in_([
                    OrderStatus.PENDING.value,
                    OrderStatus.PENDING_CONFIRM.value,
                    OrderStatus.SUBMITTED.value,
                    OrderStatus.PARTIAL_FILL.value,
                ]),
            )
        ).order_by(Order.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_orders_by_symbol(self, account_id: uuid.UUID, symbol: str) -> List[Order]:
        return await self.find_many(
            account_id=account_id, symbol=symbol,
            order_by="created_at", descending=True,
        )

    async def get_orders_by_strategy(self, account_id: uuid.UUID, strategy_name: str) -> List[Order]:
        return await self.find_many(
            account_id=account_id, strategy_name=strategy_name,
            order_by="created_at", descending=True,
        )

    async def count_daily_orders(self, account_id: uuid.UUID, trade_date: str) -> int:
        """Count orders created on a specific date."""
        from sqlalchemy import func, cast, Date
        stmt = select(func.count()).select_from(Order).where(
            and_(
                Order.account_id == account_id,
                func.date(Order.created_at) == trade_date,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_status(
        self,
        order_id: uuid.UUID,
        status: str,
        broker_order_id: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        filled_quantity: Optional[int] = None,
        avg_fill_price: Optional[float] = None,
    ) -> Optional[Order]:
        """Update order status and related fields."""
        data = {"status": status}
        if broker_order_id is not None:
            data["broker_order_id"] = broker_order_id
        if rejection_reason is not None:
            data["rejection_reason"] = rejection_reason
        if filled_quantity is not None:
            data["filled_quantity"] = filled_quantity
        if avg_fill_price is not None:
            data["avg_fill_price"] = avg_fill_price
        return await self.update(order_id, data)

    async def client_order_id_exists(self, client_order_id: str) -> bool:
        return await self.exists(client_order_id=client_order_id)
