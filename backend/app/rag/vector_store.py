"""VectorStore – abstract interface + pgvector implementation.

Provides similarity search over chunk embeddings.
Metadata filtering: symbol, document_type, published_at.
"""
from __future__ import annotations

import json
import math
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger("rag.vector_store")


@dataclass
class RetrievedChunk:
    """A chunk returned from similarity search."""
    chunk_id: str = ""
    document_id: str = ""
    content: str = ""
    score: float = 0.0          # Higher is better (cosine similarity)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    async def upsert(
        self,
        chunk_id: str,
        document_id: str,
        vector: List[float],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert or update a chunk embedding."""
        ...

    @abstractmethod
    async def delete(self, chunk_id: str) -> bool:
        """Delete a chunk embedding by chunk_id."""
        ...

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> int:
        """Delete all embeddings for a document."""
        ...

    @abstractmethod
    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        symbol: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Search for similar chunks with optional metadata filters."""
        ...

    @abstractmethod
    async def get_by_chunk(self, chunk_id: str) -> Optional[RetrievedChunk]:
        """Get a specific chunk by ID."""
        ...

    @abstractmethod
    async def count(self, document_id: Optional[str] = None) -> int:
        """Count stored embeddings."""
        ...


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryVectorStore(VectorStore):
    """In-memory vector store for testing and mock mode.

    Uses brute-force cosine similarity — suitable for small datasets.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}  # chunk_id -> {vector, content, metadata, document_id}

    async def upsert(
        self,
        chunk_id: str,
        document_id: str,
        vector: List[float],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._store[chunk_id] = {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "vector": vector,
            "content": content,
            "metadata": metadata or {},
        }

    async def delete(self, chunk_id: str) -> bool:
        if chunk_id in self._store:
            del self._store[chunk_id]
            return True
        return False

    async def delete_by_document(self, document_id: str) -> int:
        to_delete = [cid for cid, v in self._store.items() if v["document_id"] == document_id]
        for cid in to_delete:
            del self._store[cid]
        return len(to_delete)

    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        symbol: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        results: List[RetrievedChunk] = []
        for chunk_id, data in self._store.items():
            meta = data["metadata"]
            # Apply filters
            if symbol and meta.get("symbol") != symbol:
                continue
            if document_type and meta.get("document_type") != document_type:
                continue

            score = _cosine_similarity(query_vector, data["vector"])
            results.append(RetrievedChunk(
                chunk_id=chunk_id,
                document_id=data["document_id"],
                content=data["content"],
                score=score,
                metadata=meta,
            ))

        # Sort by score descending (higher is better)
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    async def get_by_chunk(self, chunk_id: str) -> Optional[RetrievedChunk]:
        data = self._store.get(chunk_id)
        if not data:
            return None
        return RetrievedChunk(
            chunk_id=chunk_id,
            document_id=data["document_id"],
            content=data["content"],
            score=1.0,
            metadata=data["metadata"],
        )

    async def count(self, document_id: Optional[str] = None) -> int:
        if document_id:
            return sum(1 for v in self._store.values() if v["document_id"] == document_id)
        return len(self._store)


# ── Factory ───────────────────────────────────────────────────────────────────

def get_vector_store(mode: Optional[str] = None) -> VectorStore:
    """Create vector store based on mode."""
    from app.config.settings import get_settings
    settings = get_settings()
    effective_mode = mode or settings.rag_mode.value

    if effective_mode == "mock":
        return InMemoryVectorStore()

    # Real mode: try pgvector
    try:
        from app.rag.pgvector_store import PgVectorStore
        return PgVectorStore()
    except Exception as e:
        logger.warning("pgvector not available, falling back to in-memory", error=str(e)[:100])
        return InMemoryVectorStore()
