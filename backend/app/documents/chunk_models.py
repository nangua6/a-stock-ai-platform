"""DocumentChunk ORM model.

Deterministic chunking: Document → DocumentChunk[].
Each chunk has stable identity and dedup hash.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentChunk(Base):
    """A deterministic chunk of a Document.

    Identity: chunk_id (stable, from document_id + chunk_index + chunk_hash)
    Dedup: chunk_hash (content-based)
    """
    __tablename__ = "document_chunks"

    # Internal PK
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True,
        comment="Internal UUID",
    )

    # Stable chunk identity (deterministic)
    chunk_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
        comment="Stable chunk ID, e.g. chunk_doc_xxx_000_abc123",
    )

    # Parent document reference
    document_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        comment="FK to documents.document_id",
    )

    # Chunk position
    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
        comment="0-based index within document",
    )

    # Content
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Chunk text content",
    )

    # Dedup hash (normalized content)
    chunk_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="sha256 of normalized content",
    )

    # Metadata (inherited from Document + chunk-specific)
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="JSON: symbol, document_type, source, published_at, report_period, chunk_index, chunk_count",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_index"),
        Index("ix_chunk_doc_id", "document_id"),
        {"comment": "Deterministic document chunks for RAG"},
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk {self.chunk_id} doc={self.document_id} idx={self.chunk_index}>"
