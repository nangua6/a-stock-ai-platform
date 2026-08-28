"""PgVectorStore – pgvector-based vector store implementation.

Requires:
- PostgreSQL with pgvector extension
- ChunkEmbedding table
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, text

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.rag.models import ChunkEmbedding
from app.rag.vector_store import RetrievedChunk, VectorStore

logger = get_logger("rag.pgvector_store")


class PgVectorStore(VectorStore):
    """PostgreSQL pgvector-based vector store.

    Uses cosine distance for similarity search.
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

        async with get_db_context() as session:
            # Check if exists
            existing = await session.execute(
                select(ChunkEmbedding).where(
                    ChunkEmbedding.chunk_id == chunk_id,
                    ChunkEmbedding.model == model_name,
                )
            )
            emb = existing.scalar_one_or_none()

            if emb:
                # Update
                emb.vector_json = json.dumps(vector)
                emb.content_hash = content_hash
                emb.dimension = len(vector)
            else:
                # Insert
                emb = ChunkEmbedding(
                    id=str(uuid.uuid4()),
                    chunk_id=chunk_id,
                    document_id=document_id,
                    symbol=meta.get("symbol", ""),
                    document_type=meta.get("document_type", ""),
                    model=model_name,
                    dimension=len(vector),
                    vector_json=json.dumps(vector),
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
        """Search using pgvector cosine distance."""
        async with get_db_context() as session:
            # Build query with optional filters
            # Use pgvector's <=> operator for cosine distance
            vector_str = f"[{','.join(str(v) for v in query_vector)}]"

            query_sql = """
                SELECT chunk_id, document_id, symbol, document_type,
                       1 - (vector_json <=> :query_vec::vector) as score
                FROM chunk_embeddings
                WHERE 1=1
            """
            params: Dict[str, Any] = {"query_vec": vector_str, "top_k": top_k}

            if symbol:
                query_sql += " AND symbol = :symbol"
                params["symbol"] = symbol
            if document_type:
                query_sql += " AND document_type = :document_type"
                params["document_type"] = document_type

            query_sql += " ORDER BY score DESC LIMIT :top_k"

            result = await session.execute(text(query_sql), params)
            rows = result.fetchall()

            return [
                RetrievedChunk(
                    chunk_id=row[0],
                    document_id=row[1],
                    content="",
                    score=float(row[4]),
                    metadata={"symbol": row[2], "document_type": row[3]},
                )
                for row in rows
            ]

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
