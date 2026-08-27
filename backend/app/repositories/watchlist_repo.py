"""Watchlist repository."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.watchlist import WatchlistItem
from app.repositories.base import BaseRepository


class WatchlistRepository(BaseRepository[WatchlistItem]):
    """Repository for watchlist operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(WatchlistItem, session)

    async def get_by_user(self, user_id: uuid.UUID) -> List[WatchlistItem]:
        """Get all watchlist items for a user."""
        result = await self.session.execute(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_and_symbol(
        self, user_id: uuid.UUID, symbol: str
    ) -> Optional[WatchlistItem]:
        """Get a specific watchlist item."""
        result = await self.session.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.symbol == symbol,
            )
        )
        return result.scalar_one_or_none()

    async def add_item(
        self, user_id: uuid.UUID, symbol: str, name: str = ""
    ) -> WatchlistItem:
        """Add a stock to watchlist. Idempotent – returns existing if already there."""
        existing = await self.get_by_user_and_symbol(user_id, symbol)
        if existing:
            return existing
        return await self.create({
            "user_id": user_id,
            "symbol": symbol,
            "name": name,
        })

    async def remove_item(self, user_id: uuid.UUID, symbol: str) -> bool:
        """Remove a stock from watchlist. Returns True if removed."""
        item = await self.get_by_user_and_symbol(user_id, symbol)
        if item is None:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True

    async def is_in_watchlist(self, user_id: uuid.UUID, symbol: str) -> bool:
        """Check if a stock is in the user's watchlist."""
        return await self.exists(user_id=user_id, symbol=symbol)
