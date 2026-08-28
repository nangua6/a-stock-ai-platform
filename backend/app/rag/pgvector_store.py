"""PgVectorStore – PostgreSQL vector store with cosine similarity.

Uses vector_json (JSON array) for storage. When pgvector is available,
uses pgvector SQL operators for efficient similarity search.
Otherwise falls back to Python-side computation.
"""
from __future__ import annotations

import json
import math
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, text

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.rag.models import ChunkEmbedding
from app.rag.vector_store import RetrievedChunk, VectorStore, _cosine_similarity

logger = get_logger("rag.pgvector_store")


class PgVectorStore(VectorStore):
    """PostgreSQL-based vector store.

    Score = cosine similarity (higher = more similar).
    """

    def __init__(self, model: str = "", dimension: int = 1536):
        self._model = model
        self._dimension = dimension

    async def upsert(
        self,
        chunk_id: str,
        document_id: str,
        vector: List[float],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert or update a chunk embedding."""
        meta = metadata or {}
        content_hash = meta.get("content_hash", "")
        model_name = meta.get("model", self._model)
        vector_str = json.dumps(vector)

        async with get_db_context() as session:
            existing = await session.execute(
                select(ChunkEmbedding).where(
                    ChunkEmbedding.chunk_id == chunk_id,
                    ChunkEmbedding.model == model_name,
                )
            )
            emb = existing.scalar_one_or_none()

            if emb:
                emb.vector_json = vector_str
                emb.content_hash = content_hash
                emb.dimension = len(vector)
            else:
                emb = ChunkEmbedding(
                    id=str(uuid.uuid4()),
                    chunk_id=chunk_id,
                    document_id=document_id,
                    symbol=meta.get("symbol", ""),
                    document_type=meta.get("document_type", ""),
                    model=model_name,
                    dimension=len(vector),
                    vector_json=vector_str,
                    content_hash=content_hash,
                )
                session.add(emb)
            await session.flush()

    async def delete(self, chunk_id: str) -> bool:
        async with get_db_context() as session:
            result = await session.execute(
                delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk_id)
            )
            await session.flush()
            return result.rowcount > 0

    async def delete_by_document(self, document_id: str) -> int:
        async with get_db_context() as session:
            result = await session.execute(
                delete(ChunkEmbedding).where(ChunkEmbedding.document_id == document_id)
            )
            await session.flush()
            return result.rowcount

    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        symbol: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Search for similar chunks.

        Uses Python-side cosine similarity for JSON-stored vectors.
        When pgvector vector column is available, use SQL cosine distance.
        """
        async with get_db_context() as session:
            stmt = select(ChunkEmbedding)
            if symbol:
                stmt = stmt.where(ChunkEmbedding.symbol == symbol)
            if document_type:
                stmt = stmt.where(ChunkEmbedding.document_type == document_type)

            result = await session.execute(stmt)
            rows = result.scalars().all()

            scored: List[RetrievedChunk] = []
            for emb in rows:
                try:
                    stored_vector = json.loads(emb.vector_json)
                    score = _cosine_similarity(query_vector, stored_vector)
                except (json.JSONDecodeError, ValueError):
                    score = 0.0

                scored.append(RetrievedChunk(
                    chunk_id=emb.chunk_id,
                    document_id=emb.document_id,
                    content="",
                    score=score,
                    metadata={
                        "symbol": emb.symbol,
                        "document_type": emb.document_type,
                        "model": emb.model,
                    },
                ))

            scored.sort(key=lambda x: x.score, reverse=True)
            return scored[:top_k]

    async def get_by_chunk(self, chunk_id: str) -> Optional[RetrievedChunk]:
        async with get_db_context() as session:
            result = await session.execute(
                select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk_id)
            )
            emb = result.scalar_one_or_none()
            if not emb:
                return None
            return RetrievedChunk(
                chunk_id=emb.chunk_id,
                document_id=emb.document_id,
                content="",
                score=1.0,
                metadata={
                    "symbol": emb.symbol,
                    "document_type": emb.document_type,
                    "model": emb.model,
                },
            )

    async def count(self, document_id: Optional[str] = None) -> int:
        async with get_db_context() as session:
            stmt = select(func.count()).select_from(ChunkEmbedding)
            if document_id:
                stmt = stmt.where(ChunkEmbedding.document_id == document_id)
            result = await session.execute(stmt)
            return result.scalar_one()
