"""
Generic async repository base class.

Provides common CRUD operations for all models.
Uses the Unit of Work pattern – repositories receive a session, not create one.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository with CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> Optional[ModelType]:
        """Get a single record by UUID primary key."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
    ) -> List[ModelType]:
        """Get all records with pagination."""
        stmt = select(self.model)
        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            stmt = stmt.order_by(col)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **filters) -> int:
        """Count records, optionally with filters."""
        stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def find_one(self, **filters) -> Optional[ModelType]:
        """Find a single record matching filters."""
        stmt = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def find_many(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        descending: bool = False,
        **filters,
    ) -> List[ModelType]:
        """Find records matching filters with pagination."""
        stmt = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            stmt = stmt.order_by(col.desc() if descending else col.asc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: Dict[str, Any]) -> ModelType:
        """Create a new record from a dict of field values."""
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: uuid.UUID, data: Dict[str, Any]) -> Optional[ModelType]:
        """Update a record by ID. Returns updated instance or None."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete_by_id(self, id: uuid.UUID) -> bool:
        """Delete a record by ID. Returns True if deleted."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def exists(self, **filters) -> bool:
        """Check if a record exists matching filters."""
        stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
