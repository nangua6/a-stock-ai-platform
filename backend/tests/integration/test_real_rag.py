"""Real RAG integration tests.

Requires:
- PostgreSQL running (docker compose up -d postgres)
- alembic upgrade head
- OPENAI_API_KEY in .env (for real embedding)

Run on macOS:
    cd backend && source .venv/bin/activate
    HTTP_PROXY='' HTTPS_PROXY='' ALL_PROXY='' NO_PROXY='*' \
    pytest tests/integration/test_real_rag.py -v -m integration
"""
import pytest
import json
import uuid


@pytest.mark.integration
class TestRealPgVectorTables:
    """Verify PostgreSQL tables and pgvector extension."""

    @pytest.mark.asyncio
    async def test_documents_table(self):
        from app.core.database import get_db_context
        from sqlalchemy import text
        async with get_db_context() as session:
            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='documents')")
            )
            assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_document_chunks_table(self):
        from app.core.database import get_db_context
        from sqlalchemy import text
        async with get_db_context() as session:
            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='document_chunks')")
            )
            assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_chunk_embeddings_table(self):
        from app.core.database import get_db_context
        from sqlalchemy import text
        async with get_db_context() as session:
            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='chunk_embeddings')")
            )
            assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_pgvector_extension(self):
        from app.core.database import get_db_context
        from sqlalchemy import text
        async with get_db_context() as session:
            result = await session.execute(
                text("SELECT extname FROM pg_extension WHERE extname='vector'")
            )
            assert result.scalar() == "vector"

    @pytest.mark.asyncio
    async def test_embedding_column_is_vector_type(self):
        """Verify embedding column uses pgvector vector type, not text."""
        from app.core.database import get_db_context
        from sqlalchemy import text
        async with get_db_context() as session:
            result = await session.execute(text("""
                SELECT data_type, udt_name
                FROM information_schema.columns
                WHERE table_name='chunk_embeddings' AND column_name='embedding'
            """))
            row = result.fetchone()
            assert row is not None
            # udt_name should be 'vector' for pgvector type
            assert row[1] == "vector", f"Expected 'vector', got '{row[1]}'"


@pytest.mark.integration
class TestRealEmbedding:
    """Test real OpenAI embedding API."""

    @pytest.mark.asyncio
    async def test_embedding_smoke(self):
        """Smoke test: embed a single query."""
        from app.rag.embedding import get_embedding_provider
        provider = get_embedding_provider(mode="real")

        vector = await provider.embed_query("贵州茅台最近公告")

        assert len(vector) > 0
        assert len(vector) == provider.dimension
        assert all(isinstance(v, float) for v in vector)
        assert not any(v != v for v in vector)  # No NaN

    @pytest.mark.asyncio
    async def test_embedding_batch(self):
        from app.rag.embedding import get_embedding_provider
        provider = get_embedding_provider(mode="real")

        texts = ["贵州茅台", "平安银行", "五粮液"]
        vectors = await provider.embed(texts)

        assert len(vectors) == 3
        assert all(len(v) == provider.dimension for v in vectors)

    @pytest.mark.asyncio
    async def test_embedding_dimension_matches_config(self):
        from app.rag.embedding import get_embedding_provider
        from app.config.settings import get_settings
        settings = get_settings()

        provider = get_embedding_provider(mode="real")
        vector = await provider.embed_query("test")

        assert len(vector) == settings.embedding_dimension

    @pytest.mark.asyncio
    async def test_embedding_deterministic(self):
        """Same input → same output (OpenAI embeddings are deterministic)."""
        from app.rag.embedding import get_embedding_provider
        provider = get_embedding_provider(mode="real")

        v1 = await provider.embed_query("贵州茅台半年报")
        v2 = await provider.embed_query("贵州茅台半年报")

        assert v1 == v2


@pytest.mark.integration
class TestRealPgVectorStore:
    """Test PgVectorStore with real PostgreSQL + pgvector."""

    @pytest.mark.asyncio
    async def test_insert_and_search(self):
        """Insert embedding and search via pgvector cosine distance."""
        from app.rag.pgvector_store import PgVectorStore
        from app.rag.embedding import get_embedding_provider

        store = PgVectorStore(model="text-embedding-3-small", dimension=1536)
        provider = get_embedding_provider(mode="real")

        test_id = uuid.uuid4().hex[:8]
        chunk_id = f"test_chunk_{test_id}"

        # Embed and insert
        vec = await provider.embed_query("贵州茅台关于回购的公告")
        await store.upsert(
            chunk_id=chunk_id,
            document_id=f"test_doc_{test_id}",
            vector=vec,
            content="贵州茅台关于回购的公告",
            metadata={
                "symbol": "600519.SH",
                "document_type": "ANNOUNCEMENT",
                "model": provider.model_name,
                "content_hash": f"test_hash_{test_id}",
            },
        )

        # Search
        query_vec = await provider.embed_query("茅台回购公告")
        results = await store.similarity_search(
            query_vec, top_k=5, symbol="600519.SH",
        )

        assert len(results) > 0
        assert results[0].score > 0.5  # Should be similar
        assert results[0].chunk_id == chunk_id

        # Cleanup
        await store.delete(chunk_id)

    @pytest.mark.asyncio
    async def test_metadata_filter(self):
        """Verify symbol and document_type filters work."""
        from app.rag.pgvector_store import PgVectorStore
        from app.rag.embedding import get_embedding_provider

        store = PgVectorStore()
        provider = get_embedding_provider(mode="real")

        test_id = uuid.uuid4().hex[:8]
        vec = await provider.embed_query("测试内容")

        # Insert with different symbols
        await store.upsert(f"c1_{test_id}", f"d1_{test_id}", vec, "a",
                           {"symbol": "600519.SH", "document_type": "NEWS", "model": provider.model_name, "content_hash": "h1"})
        await store.upsert(f"c2_{test_id}", f"d2_{test_id}", vec, "b",
                           {"symbol": "000001.SZ", "document_type": "NEWS", "model": provider.model_name, "content_hash": "h2"})

        # Filter by symbol
        results = await store.similarity_search(vec, top_k=10, symbol="600519.SH")
        assert all(r.metadata["symbol"] == "600519.SH" for r in results)

        # Cleanup
        await store.delete(f"c1_{test_id}")
        await store.delete(f"c2_{test_id}")

    @pytest.mark.asyncio
    async def test_delete_by_document(self):
        from app.rag.pgvector_store import PgVectorStore
        from app.rag.embedding import get_embedding_provider

        store = PgVectorStore()
        provider = get_embedding_provider(mode="real")
        test_id = uuid.uuid4().hex[:8]
        doc_id = f"test_doc_del_{test_id}"

        vec = await provider.embed_query("测试删除")
        await store.upsert(f"c1_{test_id}", doc_id, vec, "a",
                           {"symbol": "600519.SH", "model": provider.model_name, "content_hash": "h1"})
        await store.upsert(f"c2_{test_id}", doc_id, vec, "b",
                           {"symbol": "600519.SH", "model": provider.model_name, "content_hash": "h2"})

        deleted = await store.delete_by_document(doc_id)
        assert deleted == 2
        assert await store.count(document_id=doc_id) == 0
