"""PgVectorStore – native pgvector vector store.

Uses PostgreSQL pgvector extension with Vector(N) column type.
Cosine distance via <=> SQL operator. Score = 1 - distance.
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


def _vector_to_pgstring(vector: List[float]) -> str:
    """Convert Python list to pgvector string format: '[1.0,2.0,3.0]'"""
    return "[" + ",".join(str(v) for v in vector) + "]"


class PgVectorStore(VectorStore):
    """PostgreSQL pgvector-based vector store.

    Uses native Vector(N) column and <=> cosine distance operator.
    Score = 1 - cosine_distance (higher = more similar).
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
        """Insert or update a chunk embedding using native pgvector."""
        meta = metadata or {}
        content_hash = meta.get("content_hash", "")
        model_name = meta.get("model", self._model)
        vector_str = _vector_to_pgstring(vector)

        async with get_db_context() as session:
            existing = await session.execute(
                select(ChunkEmbedding).where(
                    ChunkEmbedding.chunk_id == chunk_id,
                    ChunkEmbedding.model == model_name,
                )
            )
            emb = existing.scalar_one_or_none()

            if emb:
                # Update via raw SQL for native vector type
                await session.execute(
                    text("UPDATE chunk_embeddings SET embedding = :vec::vector, content_hash = :ch, dimension = :dim, updated_at = NOW() WHERE id = :id"),
                    {"vec": vector_str, "ch": content_hash, "dim": len(vector), "id": emb.id},
                )
            else:
                # Insert via raw SQL for native vector type
                await session.execute(
                    text("""
                        INSERT INTO chunk_embeddings (id, chunk_id, document_id, symbol, document_type, model, dimension, embedding, content_hash)
                        VALUES (:id, :cid, :did, :sym, :dtype, :model, :dim, :vec::vector, :ch)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "cid": chunk_id,
                        "did": document_id,
                        "sym": meta.get("symbol", ""),
                        "dtype": meta.get("document_type", ""),
                        "model": model_name,
                        "dim": len(vector),
                        "vec": vector_str,
                        "ch": content_hash,
                    },
                )
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
        """Search using native pgvector cosine distance (<=>).

        Score = 1 - cosine_distance (higher = more similar).
        SQL: ORDER BY embedding <=> query_vector
        """
        async with get_db_context() as session:
            vector_str = _vector_to_pgstring(query_vector)

            query_sql = """
                SELECT ce.chunk_id, ce.document_id, ce.symbol, ce.document_type,
                       1 - (ce.embedding <=> :query_vec::vector) as score
                FROM chunk_embeddings ce
                WHERE 1=1
            """
            params: Dict[str, Any] = {"query_vec": vector_str, "top_k": top_k}

            if symbol:
                query_sql += " AND ce.symbol = :symbol"
                params["symbol"] = symbol
            if document_type:
                query_sql += " AND ce.document_type = :document_type"
                params["document_type"] = document_type

            query_sql += " ORDER BY ce.embedding <=> :query_vec::vector LIMIT :top_k"

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
