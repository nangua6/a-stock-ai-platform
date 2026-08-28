"""DocumentNormalizer – converts domain models to unified Document.

Provider → Domain Model → Normalizer → Document → Repository

Keeps providers independent of database.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Optional

from app.core.logging import get_logger
from app.documents.models import Document, DocumentType
from app.market.base import AnnouncementItem, FinancialData, NewsItem

logger = get_logger("documents.normalizer")


def _generate_document_id(document_type: DocumentType, symbol: str, content_hash: str) -> str:
    """Generate stable document_id from type, symbol, and content hash."""
    type_part = document_type.value.lower()
    sym = symbol.replace(".", "_") if symbol else "general"
    return f"doc_{sym}_{type_part}_{content_hash[:12]}"


def _stable_hash(title: str, url: str) -> str:
    """Generate deterministic content_hash from title + url."""
    raw = f"{title.strip()}|{url.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class DocumentNormalizer:
    """Normalizes domain models into unified Document instances."""

    @staticmethod
    def from_news_item(item: NewsItem) -> Document:
        """Convert NewsItem → Document."""
        content_hash = item.content_hash or _stable_hash(item.title, item.url)
        doc_id = _generate_document_id(DocumentType.NEWS, item.symbols[0] if item.symbols else "", content_hash)

        # Build content from available fields
        content = item.content or ""
        if not content and item.summary:
            content = item.summary

        return Document(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            document_type=DocumentType.NEWS,
            symbol=item.symbols[0] if item.symbols else "",
            title=item.title,
            summary=item.summary,
            content=content,
            source=item.source,
            url=item.url,
            published_at=item.published_at,
            retrieved_at=item.retrieved_at,
            report_period=None,
            metadata_json=None,
            generated_from_structured_data=False,
            content_hash=content_hash,
            data_quality=item.data_quality or "UNKNOWN",
        )

    @staticmethod
    def from_announcement_item(item: AnnouncementItem) -> Document:
        """Convert AnnouncementItem → Document."""
        content_hash = item.content_hash or _stable_hash(item.title, item.url)
        doc_id = _generate_document_id(DocumentType.ANNOUNCEMENT, item.symbol, content_hash)

        # Store announcement_type in metadata
        metadata = json.dumps({"announcement_type": item.announcement_type}, ensure_ascii=False)

        content = item.content or ""
        if not content:
            content = item.title  # At minimum, use title as content for future chunking

        return Document(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            document_type=DocumentType.ANNOUNCEMENT,
            symbol=item.symbol,
            title=item.title,
            summary=item.summary,
            content=content,
            source=item.source,
            url=item.url,
            published_at=item.published_at,
            retrieved_at=item.retrieved_at,
            report_period=None,
            metadata_json=metadata,
            generated_from_structured_data=False,
            content_hash=content_hash,
            data_quality=item.data_quality or "UNKNOWN",
        )

    @staticmethod
    def from_financial_data(data: FinancialData) -> Document:
        """Convert FinancialData → Document.

        Financial data is structured, so we generate a summary.
        Mark generated_from_structured_data = True.
        """
        # Build content summary from structured fields
        parts = []
        if data.revenue is not None:
            parts.append(f"营业收入: {data.revenue:,.0f}")
        if data.revenue_yoy is not None:
            parts.append(f"营收同比增长: {data.revenue_yoy:.2f}%")
        if data.net_profit is not None:
            parts.append(f"净利润: {data.net_profit:,.0f}")
        if data.net_profit_yoy is not None:
            parts.append(f"净利润同比增长: {data.net_profit_yoy:.2f}%")
        if data.roe is not None:
            parts.append(f"ROE: {data.roe:.2f}%")
        if data.gross_margin is not None:
            parts.append(f"毛利率: {data.gross_margin:.2f}%")
        if data.net_margin is not None:
            parts.append(f"净利率: {data.net_margin:.2f}%")
        if data.pe_ratio is not None:
            parts.append(f"PE: {data.pe_ratio:.2f}")
        if data.pb_ratio is not None:
            parts.append(f"PB: {data.pb_ratio:.2f}")

        content = "; ".join(parts) if parts else ""
        title = f"{data.symbol} 财务数据"
        if data.report_period:
            title += f" ({data.report_period})"

        # Generate deterministic hash from symbol + report_period
        hash_input = f"{data.symbol}|{data.report_period or ''}|financial"
        content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        doc_id = _generate_document_id(DocumentType.FINANCIAL, data.symbol, content_hash)

        return Document(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            document_type=DocumentType.FINANCIAL,
            symbol=data.symbol,
            title=title,
            summary=content[:200] if content else None,
            content=content,
            source=data.data_source or None,
            url=None,
            published_at=data.published_at,
            retrieved_at=data.retrieved_at,
            report_period=data.report_period,
            metadata_json=None,
            generated_from_structured_data=True,
            content_hash=content_hash,
            data_quality=data.data_quality or "UNKNOWN",
        )
