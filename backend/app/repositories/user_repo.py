"""User repository with domain-specific queries."""
from __future__ import annotations

import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self.find_one(username=username)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.find_one(email=email)

    async def get_active_users(self) -> List[User]:
        return await self.find_many(is_active=True)

    async def username_exists(self, username: str) -> bool:
        return await self.exists(username=username)

    async def email_exists(self, email: str) -> bool:
        return await self.exists(email=email)
