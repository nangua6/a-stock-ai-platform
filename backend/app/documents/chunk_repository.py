"""DocumentChunkRepository – persistence for document chunks.

Provides idempotent insert: same document → same chunks, no duplicates.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.chunk_models import DocumentChunk
from app.repositories.base import BaseRepository


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """Repository for DocumentChunk CRUD + idempotent operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(DocumentChunk, session)

    async def get_by_chunk_id(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Get a chunk by its stable chunk_id."""
        return await self.find_one(chunk_id=chunk_id)

    async def find_by_document(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a document, ordered by chunk_index."""
        return await self.find_many(
            document_id=document_id,
            limit=1000,
            order_by="chunk_index",
            descending=False,
        )

    async def find_by_hash(self, chunk_hash: str) -> Optional[DocumentChunk]:
        """Find a chunk by its content hash."""
        return await self.find_one(chunk_hash=chunk_hash)

    async def upsert_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Idempotently insert chunks for a document.

        If chunks already exist for this document with same content, skip.
        Strategy: delete old chunks for this document, then insert new ones.
        This ensures no stale/old-new mixing.
        """
        if not chunks:
            return []

        document_id = chunks[0].document_id

        # Check if identical chunks already exist
        existing = await self.find_by_document(document_id)
        if existing:
            existing_hashes = [c.chunk_hash for c in existing]
            new_hashes = [c.chunk_hash for c in chunks]
            if existing_hashes == new_hashes:
                # Identical — no change needed
                return existing
            # Different — delete old, insert new
            await self.delete_by_document(document_id)

        # Insert new chunks
        result = []
        for chunk in chunks:
            if not chunk.id:
                chunk.id = str(uuid.uuid4())
            self.session.add(chunk)
            result.append(chunk)

        await self.session.flush()
        for chunk in result:
            await self.session.refresh(chunk)
        return result

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document. Returns count deleted."""
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def count_by_document(self, document_id: str) -> int:
        """Count chunks for a document."""
        return await self.count(document_id=document_id)
