"""EmbeddingProvider – abstract interface + OpenAI-compatible + Mock.

Real provider: OpenAI text-embedding-3-small (1536-dim, excellent Chinese support).
Mock provider: deterministic hash-based vectors for unit tests.

All embedding calls go through this client. NEVER call APIs directly.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger("rag.embedding")

MAX_RETRIES = 3
BASE_DELAY = 1.0
REQUEST_TIMEOUT = 30.0
DEFAULT_BATCH_SIZE = 64


class EmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts. Returns list of vectors."""
        ...

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query text."""
        results = await self.embed([text])
        return results[0]


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock embedding for unit tests. No network, no API key."""

    def __init__(self, dimension: int = 128):
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return "mock-embedding-v1"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            vector = []
            for i in range(self._dimension):
                byte_val = h[i % len(h)]
                vector.append((byte_val / 127.5) - 1.0)
            results.append(vector)
        return results


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding via OpenAI /embeddings API.

    Default model: text-embedding-3-small (1536-dim, excellent Chinese).
    Supports batch embedding with retry + exponential backoff.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimension = dimension
        self._batch_size = batch_size

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed texts in batches with retry."""
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i:i + self._batch_size]
            batch_embeddings = await self._embed_batch_with_retry(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _embed_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch with exponential backoff retry."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            start = time.time()
            try:
                result = await self._call_api(texts)
                elapsed = time.time() - start
                logger.info(
                    "embedding_batch_ok",
                    model=self._model,
                    count=len(texts),
                    attempt=attempt + 1,
                    latency_ms=round(elapsed * 1000, 1),
                )
                return result
            except Exception as e:
                elapsed = time.time() - start
                last_error = f"{type(e).__name__}: {str(e)[:200]}"
                logger.warning(
                    "embedding_batch_failed",
                    model=self._model,
                    count=len(texts),
                    attempt=attempt + 1,
                    error=last_error,
                    latency_ms=round(elapsed * 1000, 1),
                )
                if attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt), 10.0)
                    await asyncio.sleep(delay)

        raise ConnectionError(f"Embedding failed after {MAX_RETRIES} retries: {last_error}")

    async def _call_api(self, texts: List[str]) -> List[List[float]]:
        """Call OpenAI /embeddings API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)

        response = await client.embeddings.create(
            model=self._model,
            input=texts,
        )

        # Sort by index to ensure correct ordering
        sorted_data = sorted(response.data, key=lambda x: x.index)
        embeddings = [item.embedding for item in sorted_data]

        if len(embeddings) != len(texts):
            raise ValueError(f"Expected {len(texts)} embeddings, got {len(embeddings)}")

        # Verify dimension
        if embeddings and len(embeddings[0]) != self._dimension:
            actual = len(embeddings[0])
            logger.warning("embedding_dimension_mismatch", expected=self._dimension, actual=actual)
            self._dimension = actual

        return embeddings


# ── Factory ───────────────────────────────────────────────────────────────────

def get_embedding_provider(mode: Optional[str] = None) -> EmbeddingProvider:
    """Create embedding provider based on mode or settings."""
    settings = get_settings()
    effective_mode = mode or settings.rag_mode.value

    if effective_mode == "mock":
        logger.info("Creating MOCK embedding provider")
        return MockEmbeddingProvider(dimension=128)

    # Real mode: use OpenAI-compatible API
    api_key = settings.embedding_api_key or settings.mimo_api_key
    base_url = settings.embedding_base_url or "https://api.openai.com/v1"
    model = settings.embedding_model
    dimension = settings.embedding_dimension

    if not api_key:
        logger.warning("No embedding API key configured, falling back to mock")
        return MockEmbeddingProvider(dimension=128)

    logger.info("Creating REAL embedding provider", model=model, dimension=dimension)
    return OpenAIEmbeddingProvider(
        api_key=api_key,
        base_url=base_url,
        model=model,
        dimension=dimension,
    )
