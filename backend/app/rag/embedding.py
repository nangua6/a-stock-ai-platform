"""EmbeddingProvider – abstract interface + OpenAI-compatible + Mock.

All embedding calls go through this client. NEVER call embedding APIs directly.
Supports batch embedding, retry, and cache.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import httpx

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger("rag.embedding")

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_BATCH_SIZE = 32
MAX_RETRIES = 3
BASE_DELAY = 1.0
REQUEST_TIMEOUT = 30.0


class EmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the embedding model identifier."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        ...

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts. Returns list of vectors."""
        ...

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query text. Returns one vector."""
        results = await self.embed([text])
        return results[0]


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock embedding for unit tests.

    Generates vectors from text hash — no network, no API key.
    """

    def __init__(self, dimension: int = 128):
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return "mock-embedding-v1"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate deterministic mock embeddings from text hash."""
        results = []
        for text in texts:
            # Generate deterministic vector from text hash
            h = hashlib.sha256(text.encode()).digest()
            # Expand hash to fill dimension
            vector = []
            for i in range(self._dimension):
                byte_val = h[i % len(h)]
                # Normalize to [-1, 1]
                vector.append((byte_val / 127.5) - 1.0)
            results.append(vector)
        return results


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Embedding via OpenAI-compatible /embeddings API.

    Works with: OpenAI, MiMo Token Plan (if supported), local servers, etc.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
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
        """Embed a single batch with exponential backoff retry."""
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
        """Call the /embeddings API endpoint."""
        url = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                raise ConnectionError(
                    f"Embedding API returned {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            embeddings = []
            for item in sorted(data.get("data", []), key=lambda x: x.get("index", 0)):
                embeddings.append(item["embedding"])

            if len(embeddings) != len(texts):
                raise ValueError(
                    f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                )

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
    base_url = settings.embedding_base_url or settings.mimo_base_url
    api_key = settings.embedding_api_key or settings.mimo_api_key

    if not base_url or not api_key:
        logger.warning("Embedding API not configured, falling back to mock")
        return MockEmbeddingProvider(dimension=128)

    logger.info(
        "Creating REAL embedding provider",
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
    )
    return OpenAICompatibleEmbeddingProvider(
        base_url=base_url,
        api_key=api_key,
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
    )
