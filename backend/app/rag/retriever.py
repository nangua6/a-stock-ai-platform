"""Retriever – query → embedding → vector search → top-k chunks.

Provides the main RAG retrieval interface for the Agent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.rag.embedding import EmbeddingProvider, get_embedding_provider
from app.rag.vector_store import RetrievedChunk, VectorStore, get_vector_store

logger = get_logger("rag.retriever")


class Retriever:
    """RAG Retriever: query → embed → search → top-k chunks.

    Flow:
        User Query
        → EmbeddingProvider.embed_query()
        → VectorStore.similarity_search()
        → Top K RetrievedChunks
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or get_vector_store()

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        symbol: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Retrieve top-k relevant chunks for a query.

        Args:
            query: User question or search query
            top_k: Number of results to return
            symbol: Filter by stock symbol (e.g. "600519.SH")
            document_type: Filter by document type (e.g. "ANNOUNCEMENT")

        Returns:
            List of RetrievedChunk, sorted by relevance (highest first).
        """
        if not query or not query.strip():
            return []

        try:
            # Step 1: Embed the query
            query_vector = await self.embedding_provider.embed_query(query)

            # Step 2: Similarity search
            results = await self.vector_store.similarity_search(
                query_vector=query_vector,
                top_k=top_k,
                symbol=symbol,
                document_type=document_type,
            )

            logger.info(
                "rag_retrieve_ok",
                query_length=len(query),
                top_k=top_k,
                symbol=symbol,
                document_type=document_type,
                results=len(results),
            )

            return results

        except Exception as e:
            logger.error("rag_retrieve_failed", error=str(e)[:200])
            return []
