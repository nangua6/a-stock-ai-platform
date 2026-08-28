"""ChunkEmbedding ORM model for pgvector storage.

Stores embedding vectors per chunk, per model.
(chunk_id, model) is unique — same chunk can have embeddings from multiple models.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChunkEmbedding(Base):
    """Embedding vector for a document chunk.

    Identity: (chunk_id, model) unique
    Vector: stored as pgvector type (requires pgvector extension)
    """
    __tablename__ = "chunk_embeddings"

    # Internal PK
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True,
        comment="Internal UUID",
    )

    # Chunk reference
    chunk_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        comment="FK to document_chunks.chunk_id",
    )

    # Document reference (for convenience, avoids join for filtering)
    document_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        comment="FK to documents.document_id",
    )

    # Symbol (denormalized for fast filtering)
    symbol: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="Normalized symbol for filtering",
    )

    # Document type (denormalized for fast filtering)
    document_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
        comment="Document type for filtering",
    )

    # Embedding model identifier
    model: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Embedding model name, e.g. text-embedding-3-small",
    )

    # Vector dimension
    dimension: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Vector dimension, e.g. 1536",
    )

    # The embedding vector — stored as text for portability, converted to pgvector at query time
    # In real pgvector mode, this would be a vector(1536) column
    # For compatibility, we store as JSON string and also have a placeholder for pgvector
    vector_json: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Embedding vector as JSON array",
    )

    # Content hash (for cache: same content + same model → skip embedding)
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="chunk_hash for cache invalidation",
    )

    # Timestamps
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
