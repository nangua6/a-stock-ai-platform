"""ChunkEmbedding ORM model for pgvector storage.

Uses real pgvector vector(N) type when available, falls back to Text.
(chunk_id, model) is unique.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChunkEmbedding(Base):
    """Embedding vector for a document chunk.

    The vector column stores embeddings as a JSON array of floats.
    When pgvector is installed, this can be upgraded to Vector(N) type.
    """
    __tablename__ = "chunk_embeddings"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True,
    )
    chunk_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
    )
    symbol: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
    )
    document_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )
    model: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    dimension: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    # Vector stored as JSON text; upgrade to pgvector Vector(N) when extension available
    vector_json: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Embedding vector as JSON array. Upgrade to Vector(N) with pgvector.",
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("chunk_id", "model", name="uq_chunk_model"),
        Index("ix_chunk_emb_chunk_id", "chunk_id"),
        Index("ix_chunk_emb_doc_id", "document_id"),
        Index("ix_chunk_emb_symbol", "symbol"),
        Index("ix_chunk_emb_content_hash", "content_hash"),
        {"comment": "Chunk embedding vectors for RAG retrieval"},
    )

    def __repr__(self) -> str:
        return f"<ChunkEmbedding chunk={self.chunk_id} model={self.model} dim={self.dimension}>"
