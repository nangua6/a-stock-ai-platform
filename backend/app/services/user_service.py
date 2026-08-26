"""User management service."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError, NotFoundError
from app.core.security import Role, hash_password, verify_password
from app.models.user import User
from app.repositories.factory import RepositoryFactory


class UserService:
    """Handles user registration, authentication, and profile management."""

    def __init__(self, session: AsyncSession):
        self.repos = RepositoryFactory(session)

    async def register(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: Role = Role.RESEARCH,
    ) -> User:
        """Register a new user."""
        if await self.repos.users.username_exists(username):
            raise ValidationError(f"Username already taken: {username}")
        if await self.repos.users.email_exists(email):
            raise ValidationError(f"Email already registered: {email}")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        user = await self.repos.users.create({
            "username": username,
            "email": email,
            "hashed_password": hash_password(password),
            "full_name": full_name,
            "role": role.value,
            "is_active": True,
        })
        return user

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username/password. Returns User or None."""
        user = await self.repos.users.get_by_username(username)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self.repos.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", str(user_id))
        return user

    async def update_role(self, user_id: uuid.UUID, role: Role) -> User:
        user = await self.get_user(user_id)
        return await self.repos.users.update(user_id, {"role": role.value})

    async def deactivate(self, user_id: uuid.UUID) -> User:
        return await self.repos.users.update(user_id, {"is_active": False})
