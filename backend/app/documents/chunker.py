"""DocumentChunker – deterministic text chunking.

Document → DocumentChunk[]

All chunking is fully deterministic (no LLM, no randomness).
Same input → identical output every time.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.logging import get_logger
from app.documents.chunk_models import DocumentChunk
from app.documents.models import Document, DocumentType

logger = get_logger("documents.chunker")

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_CHUNK_SIZE = 1000      # characters per chunk
DEFAULT_CHUNK_OVERLAP = 200    # overlap characters
MIN_CHUNK_SIZE = 100           # discard chunks shorter than this


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace without destroying numbers, dates, symbols.

    - Collapse multiple spaces/tabs to single space
    - Normalize line breaks
    - Strip leading/trailing whitespace per line
    - Preserve all digits, %, ., dates, stock codes
    """
    # Normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse spaces/tabs within lines
    text = re.sub(r'[ \t]+', ' ', text)
    # Strip each line
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines).strip()


def _stable_chunk_id(document_id: str, chunk_index: int, chunk_hash: str) -> str:
    """Generate deterministic chunk_id."""
    return f"chunk_{document_id}_{chunk_index:03d}_{chunk_hash[:10]}"


def _content_hash(content: str) -> str:
    """Hash normalized chunk content."""
    normalized = content.strip()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


# ── Base Chunker ──────────────────────────────────────────────────────────────

class DocumentChunker(ABC):
    """Abstract chunker interface."""

    @abstractmethod
    def chunk(self, document: Document) -> List[DocumentChunk]:
        """Split document into deterministic chunks."""
        ...


class BaseChunker(DocumentChunker):
    """Base chunker with paragraph-first, size-bounded splitting."""

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        min_chunk_size: int = MIN_CHUNK_SIZE,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk(self, document: Document) -> List[DocumentChunk]:
        """Split document content into chunks."""
        content = document.content
        if not content or not content.strip():
            return []

        normalized = _normalize_whitespace(content)
        if len(normalized) < self.min_chunk_size:
            # Too short to chunk — return as single chunk
            return self._make_chunks(document, [normalized])

        # Split by paragraphs first
        paragraphs = self._split_paragraphs(normalized)

        # Merge paragraphs into size-bounded chunks
        raw_chunks = self._merge_paragraphs(paragraphs)

        return self._make_chunks(document, raw_chunks)

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text by double newlines (paragraphs)."""
        parts = re.split(r'\n\s*\n', text)
        return [p.strip() for p in parts if p.strip()]

    def _merge_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """Merge paragraphs into chunks respecting size limits."""
        chunks: List[str] = []
        current = ""

        for para in paragraphs:
            if not current:
                current = para
            elif len(current) + len(para) + 2 <= self.chunk_size:
                current = f"{current}\n\n{para}"
            else:
                # Current is full, start new chunk
                if len(current) > self.chunk_size:
                    # Oversized paragraph — split by sentences/size
                    sub_chunks = self._split_oversized(current)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(current)
                current = para

        if current:
            if len(current) > self.chunk_size:
                chunks.extend(self._split_oversized(current))
            else:
                chunks.append(current)

        return chunks

    def _split_oversized(self, text: str) -> List[str]:
        """Split oversized text by size with overlap."""
        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            # Try to break at sentence/word boundary
            if end < len(text):
                # Look for sentence boundary
                for sep in ['。', '！', '？', '. ', '! ', '? ', '；', '\n']:
                    last_sep = text.rfind(sep, start + self.min_chunk_size, end)
                    if last_sep > start:
                        end = last_sep + len(sep)
                        break
                else:
                    # Fall back to word boundary
                    last_space = text.rfind(' ', start + self.min_chunk_size, end)
                    if last_space > start:
                        end = last_space + 1

            chunk = text[start:end].strip()
            if chunk and len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)

            # Advance with overlap
            start = max(end - self.chunk_overlap, start + 1) if end < len(text) else end

        return chunks

    def _make_chunks(self, document: Document, raw_chunks: List[str]) -> List[DocumentChunk]:
        """Convert raw text chunks into DocumentChunk objects."""
        # Build metadata template from Document
        base_metadata = {
            "symbol": document.symbol,
            "document_type": document.document_type.value if document.document_type else "",
            "source": document.source or "",
            "published_at": document.published_at or "",
            "report_period": document.report_period or "",
            "chunk_count": len(raw_chunks),
        }

        chunks: List[DocumentChunk] = []
        for idx, content in enumerate(raw_chunks):
            chash = _content_hash(content)
            chunk_id = _stable_chunk_id(document.document_id, idx, chash)

            metadata = {**base_metadata, "chunk_index": idx}

            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                chunk_id=chunk_id,
                document_id=document.document_id,
                chunk_index=idx,
                content=content,
                chunk_hash=chash,
                metadata_json=json.dumps(metadata, ensure_ascii=False),
            )
            chunks.append(chunk)

        return chunks


# ── Type-specific Chunkers ────────────────────────────────────────────────────

class NewsChunker(BaseChunker):
    """Chunker for news articles.

    News are typically shorter — prefer paragraph splitting.
    """
    def __init__(self):
        super().__init__(chunk_size=800, chunk_overlap=100, min_chunk_size=50)


class AnnouncementChunker(BaseChunker):
    """Chunker for company announcements.

    Announcements can be long — use standard chunk size.
    """
    def __init__(self):
        super().__init__(chunk_size=1200, chunk_overlap=200, min_chunk_size=100)


class FinancialChunker(BaseChunker):
    """Chunker for financial data summaries.

    Financial content is structured — group by logical sections.
    Since content is already concise (from DocumentNormalizer),
    use smaller chunks to keep each fact group tight.
    """
    def __init__(self):
        super().__init__(chunk_size=600, chunk_overlap=0, min_chunk_size=30)

    def chunk(self, document: Document) -> List[DocumentChunk]:
        """Split financial content by semicolons (each fact group)."""
        content = document.content
        if not content or not content.strip():
            return []

        normalized = _normalize_whitespace(content)
        if not normalized:
            return []

        # Financial content from normalizer uses "; " as separator
        parts = [p.strip() for p in normalized.split(";") if p.strip()]

        if not parts:
            return []

        # Group parts into chunks respecting size
        raw_chunks: List[str] = []
        current = ""
        for part in parts:
            if not current:
                current = part
            elif len(current) + len(part) + 2 <= self.chunk_size:
                current = f"{current}; {part}"
            else:
                raw_chunks.append(current)
                current = part
        if current:
            raw_chunks.append(current)

        return self._make_chunks(document, raw_chunks)


# ── Factory ───────────────────────────────────────────────────────────────────

def get_chunker(document_type: DocumentType) -> DocumentChunker:
    """Get the appropriate chunker for a document type."""
    if document_type == DocumentType.NEWS:
        return NewsChunker()
    elif document_type == DocumentType.ANNOUNCEMENT:
        return AnnouncementChunker()
    elif document_type == DocumentType.FINANCIAL:
        return FinancialChunker()
    return BaseChunker()
