"""Account repository."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self, session: AsyncSession):
        super().__init__(Account, session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> List[Account]:
        return await self.find_many(user_id=user_id)

    async def get_paper_accounts(self, user_id: uuid.UUID) -> List[Account]:
        return await self.find_many(user_id=user_id, account_type="PAPER")

    async def get_live_accounts(self, user_id: uuid.UUID) -> List[Account]:
        return await self.find_many(user_id=user_id, account_type="LIVE")

    async def get_active_account(self, user_id: uuid.UUID, account_type: str = "PAPER") -> Optional[Account]:
        return await self.find_one(user_id=user_id, account_type=account_type, is_active=True)

    async def update_cash(self, account_id: uuid.UUID, new_cash: float) -> Optional[Account]:
        return await self.update(account_id, {"cash": new_cash})

    async def update_total_asset(self, account_id: uuid.UUID, total_asset: float) -> Optional[Account]:
        return await self.update(account_id, {"total_asset": total_asset})

    async def add_realized_pnl(self, account_id: uuid.UUID, pnl: float) -> Optional[Account]:
        account = await self.get_by_id(account_id)
        if account:
            return await self.update(account_id, {
                "realized_pnl": account.realized_pnl + pnl,
            })
        return None
