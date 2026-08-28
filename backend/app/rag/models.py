"""ChunkEmbedding ORM model with native pgvector Vector(N) type.

Stores embedding vectors as PostgreSQL vector type for efficient
cosine similarity search via pgvector extension.
(chunk_id, model) is unique — same chunk can have embeddings from multiple models.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from pgvector.sqlalchemy import Vector


class ChunkEmbedding(Base):
    """Embedding vector for a document chunk.

    Uses native pgvector Vector(N) type.
    Identity: (chunk_id, model) unique.
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
    # Native pgvector Vector type — dimension set at migration time
    embedding = mapped_column(
        Vector(1536), nullable=False,
        comment="Embedding vector (pgvector Vector(1536))",
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
