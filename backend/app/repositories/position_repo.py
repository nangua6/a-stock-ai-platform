"""Position repository."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position import Position
from app.repositories.base import BaseRepository


class PositionRepository(BaseRepository[Position]):
    def __init__(self, session: AsyncSession):
        super().__init__(Position, session)

    async def get_by_account(self, account_id: uuid.UUID) -> List[Position]:
        return await self.find_many(account_id=account_id, is_open=True)

    async def get_by_symbol(self, account_id: uuid.UUID, symbol: str) -> Optional[Position]:
        return await self.find_one(account_id=account_id, symbol=symbol, is_open=True)

    async def get_top_positions(
        self, account_id: uuid.UUID, limit: int = 10
    ) -> List[Position]:
        return await self.find_many(
            account_id=account_id,
            is_open=True,
            order_by="market_value",
            descending=True,
            limit=limit,
        )

    async def update_price(
        self, position_id: uuid.UUID, current_price: float
    ) -> Optional[Position]:
        """Update current price and recalculate market value / PnL."""
        pos = await self.get_by_id(position_id)
        if not pos:
            return None
        market_value = pos.quantity * current_price
        unrealized_pnl = (current_price - pos.avg_cost) * pos.quantity
        unrealized_pnl_pct = (current_price / pos.avg_cost - 1) if pos.avg_cost > 0 else 0
        return await self.update(position_id, {
            "current_price": current_price,
            "market_value": round(market_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 6),
        })

    async def add_quantity(
        self, position_id: uuid.UUID, qty_delta: int, is_buy: bool
    ) -> Optional[Position]:
        """Adjust position quantity (buy adds available later for T+1)."""
        pos = await self.get_by_id(position_id)
        if not pos:
            return None
        new_qty = pos.quantity + qty_delta
        data = {"quantity": new_qty}
        if is_buy:
            data["today_buy_qty"] = pos.today_buy_qty + qty_delta
        else:
            data["available_quantity"] = pos.available_quantity - qty_delta
            data["today_sell_qty"] = pos.today_sell_qty + qty_delta
        return await self.update(position_id, data)

    async def reset_daily_quantities(self, account_id: uuid.UUID):
        """Reset daily buy/sell counts and make T+1 shares available (call at market open)."""
        positions = await self.get_by_account(account_id)
        for pos in positions:
            await self.update(pos.id, {
                "available_quantity": pos.quantity,  # T+1: yesterday's buys now available
                "today_buy_qty": 0,
                "today_sell_qty": 0,
            })
