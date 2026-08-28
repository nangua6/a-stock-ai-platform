"""Document ORM model and DocumentType enum.

Unified knowledge layer: Financial, News, Announcement → Document.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentType(str, enum.Enum):
    """Document type classification."""
    FINANCIAL = "FINANCIAL"
    NEWS = "NEWS"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    # Future extensions:
    # RESEARCH = "RESEARCH"
    # REPORT = "REPORT"
    # NOTICE = "NOTICE"
    # OTHER = "OTHER"


class Document(Base):
    """Unified document for knowledge retrieval.

    Maps from: NewsItem, AnnouncementItem, FinancialData
    Identity: document_id (stable, deterministic from source fields)
    Dedup: content_hash (unique index)
    """
    __tablename__ = "documents"

    # Primary key (auto-generated UUID for DB internal use)
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True,
        comment="Internal UUID",
    )

    # Stable document identity (deterministic from source fields)
    document_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
        comment="Stable document ID, e.g. doc_600519_announcement_abc123",
    )

    # Classification
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type_enum"),
        nullable=False, index=True,
    )

    # Stock reference
    symbol: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="Normalized symbol, e.g. 600519.SH",
    )

    # Content
    title: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None,
        comment="Brief summary (original or generated)",
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None,
        comment="Full content if available",
    )

    # Source
    source: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, default=None,
        comment="Data source, e.g. 东方财富, 证券时报",
    )
    url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None,
        comment="Original URL if available",
    )

    # Time semantics
    published_at: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, default=None, index=True,
        comment="When the document was published (from source)",
    )
    retrieved_at: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, default=None,
        comment="When we fetched this document",
    )
    report_period: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, default=None,
        comment="Financial report period, e.g. 2025-12-31",
    )

    # Metadata (JSON-like, for flexible extension)
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None,
        comment="Additional metadata as JSON string",
    )

    # Provenance flags
    generated_from_structured_data: Mapped[bool] = mapped_column(
        default=False, nullable=False,
        comment="True if content was generated from structured data (not original text)",
    )

    # Dedup
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="sha256 hash for dedup",
    )

    # Data quality
    data_quality: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNKNOWN",
        comment="GOOD / PARTIAL / UNAVAILABLE / UNKNOWN",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("ix_documents_symbol_type", "symbol", "document_type"),
        Index("ix_documents_symbol_published", "symbol", "published_at"),
        {"comment": "Unified document knowledge base"},
    )

    def __repr__(self) -> str:
        return f"<Document {self.document_id} type={self.document_type} symbol={self.symbol}>"
