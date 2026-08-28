"""DocumentRepository – persistence layer for Document knowledge base.

Provides upsert-by-hash to prevent duplicate documents.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.models import Document, DocumentType
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document CRUD + dedup queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_document_id(self, document_id: str) -> Optional[Document]:
        """Get a document by its stable document_id."""
        return await self.find_one(document_id=document_id)

    async def find_by_hash(self, content_hash: str) -> Optional[Document]:
        """Find a document by content_hash (for dedup)."""
        return await self.find_one(content_hash=content_hash)

    async def find_by_symbol(
        self,
        symbol: str,
        document_type: Optional[DocumentType] = None,
        limit: int = 50,
    ) -> List[Document]:
        """Find documents for a symbol, optionally filtered by type."""
        filters: dict = {"symbol": symbol}
        if document_type:
            filters["document_type"] = document_type
        return await self.find_many(
            limit=limit, order_by="published_at", descending=True, **filters,
        )

    async def find_by_type(
        self,
        document_type: DocumentType,
        limit: int = 50,
    ) -> List[Document]:
        """Find documents by type."""
        return await self.find_many(
            document_type=document_type, limit=limit,
            order_by="published_at", descending=True,
        )

    async def upsert(self, data: dict) -> Document:
        """Insert or skip if content_hash already exists.

        Returns the existing or newly created Document.
        """
        content_hash = data.get("content_hash")
        if not content_hash:
            raise ValueError("content_hash is required for upsert")

        existing = await self.find_by_hash(content_hash)
        if existing:
            return existing

        # Ensure document_id
        if not data.get("document_id"):
            data["document_id"] = f"doc_{uuid.uuid4().hex[:16]}"

        # Ensure internal id
        if not data.get("id"):
            data["id"] = str(uuid.uuid4())

        return await self.create(data)

    async def count_by_symbol(self, symbol: str) -> int:
        """Count documents for a symbol."""
        return await self.count(symbol=symbol)

    async def find_recent(
        self,
        symbol: Optional[str] = None,
        document_type: Optional[DocumentType] = None,
        limit: int = 20,
    ) -> List[Document]:
        """Find recent documents with optional filters."""
        filters: dict = {}
        if symbol:
            filters["symbol"] = symbol
        if document_type:
            filters["document_type"] = document_type
        return await self.find_many(
            limit=limit, order_by="published_at", descending=True, **filters,
        )
