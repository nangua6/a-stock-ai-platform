"""Account management service."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.account import Account
from app.repositories.factory import RepositoryFactory


class AccountService:
    """Manages trading accounts (paper and live)."""

    def __init__(self, session: AsyncSession):
        self.repos = RepositoryFactory(session)

    async def create_account(
        self,
        user_id: uuid.UUID,
        name: str,
        account_type: str = "PAPER",
        initial_capital: float = 1_000_000.0,
        broker: str = "mock",
    ) -> Account:
        """Create a new trading account."""
        if initial_capital < 0:
            raise ValidationError("Initial capital must be non-negative")
        if account_type not in ("PAPER", "LIVE"):
            raise ValidationError(f"Invalid account type: {account_type}")

        account = await self.repos.accounts.create({
            "user_id": user_id,
            "name": name,
            "account_type": account_type,
            "initial_capital": initial_capital,
            "cash": initial_capital,
            "total_asset": initial_capital,
            "realized_pnl": 0.0,
            "broker": broker,
            "is_active": True,
        })
        return account

    async def get_account(self, account_id: uuid.UUID) -> Account:
        account = await self.repos.accounts.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account", str(account_id))
        return account

    async def get_user_accounts(self, user_id: uuid.UUID) -> List[Account]:
        return await self.repos.accounts.get_by_user_id(user_id)

    async def get_default_paper_account(self, user_id: uuid.UUID) -> Account:
        """Get or create the default paper trading account."""
        account = await self.repos.accounts.get_active_account(user_id, "PAPER")
        if not account:
            account = await self.create_account(
                user_id=user_id,
                name="默认模拟账户",
                account_type="PAPER",
            )
        return account

    async def update_asset_snapshot(
        self,
        account_id: uuid.UUID,
        cash: float,
        market_value: float,
        realized_pnl: float,
    ) -> Account:
        """Update account with latest asset snapshot from portfolio engine."""
        return await self.repos.accounts.update(account_id, {
            "cash": round(cash, 2),
            "total_asset": round(cash + market_value, 2),
            "realized_pnl": round(realized_pnl, 2),
        })
