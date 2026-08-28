"""Real RAG integration tests.

Requires:
- PostgreSQL running (docker compose up -d postgres)
- alembic upgrade head
- EMBEDDING_API_KEY configured (or mock embedding for DB-only tests)

Run:
    cd backend && source .venv/bin/activate
    HTTP_PROXY='' HTTPS_PROXY='' ALL_PROXY='' NO_PROXY='*' \
    pytest tests/integration/test_real_rag.py -v -m integration
"""
import pytest
import json
import uuid


@pytest.mark.integration
class TestRealPgVector:
    """Test PostgreSQL + pgvector with real database."""

    @pytest.mark.asyncio
    async def test_documents_table_exists(self):
        """Verify documents table was created by migration."""
        from app.core.database import get_db_context
        from sqlalchemy import text
        async with get_db_context() as session:
            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='documents')")
            )
            assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_document_chunks_table_exists(self):
        from app.core.database import get_db_context
        from sqlalchemy import text
        async with get_db_context() as session:
            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='document_chunks')")
            )
            assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_chunk_embeddings_table_exists(self):
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
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")
            )
            # pgvector should be installed
            assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_document_crud(self):
        """Test Document insert, query, upsert."""
        from app.core.database import get_db_context
        from app.documents.models import Document, DocumentType
        from app.documents.repository import DocumentRepository
        import uuid

        doc_id = f"test_doc_{uuid.uuid4().hex[:8]}"
        content_hash = f"test_hash_{uuid.uuid4().hex[:8]}"

        async with get_db_context() as session:
            repo = DocumentRepository(session)

            # Create
            doc = await repo.upsert({
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "document_type": DocumentType.NEWS,
                "symbol": "600519.SH",
                "title": "Test Document",
                "content": "Test content for RAG",
                "source": "test",
                "content_hash": content_hash,
                "data_quality": "GOOD",
            })
            assert doc.document_id == doc_id

            # Get by hash (dedup)
            existing = await repo.find_by_hash(content_hash)
            assert existing is not None
            assert existing.document_id == doc_id

            # Upsert same hash (should return existing)
            doc2 = await repo.upsert({
                "id": str(uuid.uuid4()),
                "document_id": f"different_{uuid.uuid4().hex[:8]}",
                "document_type": DocumentType.NEWS,
                "symbol": "600519.SH",
                "title": "Test Document",
                "content": "Test content for RAG",
                "source": "test",
                "content_hash": content_hash,
                "data_quality": "GOOD",
            })
            assert doc2.document_id == doc_id  # Same as before

    @pytest.mark.asyncio
    async def test_chunk_embedding_crud(self):
        """Test ChunkEmbedding insert and query."""
        from app.core.database import get_db_context
        from app.rag.models import ChunkEmbedding
        import uuid

        chunk_id = f"test_chunk_{uuid.uuid4().hex[:8]}"

        async with get_db_context() as session:
            emb = ChunkEmbedding(
                id=str(uuid.uuid4()),
                chunk_id=chunk_id,
                document_id="test_doc",
                symbol="600519.SH",
                document_type="ANNOUNCEMENT",
                model="test-model",
                dimension=3,
                vector_json=json.dumps([1.0, 0.0, 0.0]),
                content_hash="test_hash",
            )
            session.add(emb)
            await session.flush()

            # Query
            from sqlalchemy import select
            result = await session.execute(
                select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk_id)
            )
            found = result.scalar_one()
            assert found.chunk_id == chunk_id
            assert found.dimension == 3
            assert json.loads(found.vector_json) == [1.0, 0.0, 0.0]

            # Cleanup
            await session.delete(found)
            await session.flush()


@pytest.mark.integration
class TestRealEmbeddingAPI:
    """Test real embedding API (requires EMBEDDING_API_KEY)."""

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
        """Test batch embedding."""
        from app.rag.embedding import get_embedding_provider

        provider = get_embedding_provider(mode="real")
        texts = ["贵州茅台", "平安银行", "五粮液"]
        vectors = await provider.embed(texts)

        assert len(vectors) == 3
        assert all(len(v) == provider.dimension for v in vectors)

    @pytest.mark.asyncio
    async def test_embedding_dimension_match(self):
        """Verify embedding dimension matches config."""
        from app.rag.embedding import get_embedding_provider
        from app.config.settings import get_settings

        settings = get_settings()
        provider = get_embedding_provider(mode="real")
        vector = await provider.embed_query("test")

        assert len(vector) == settings.embedding_dimension


@pytest.mark.integration
class TestRealVectorSearch:
    """Test real vector search with pgvector."""

    @pytest.mark.asyncio
    async def test_similarity_search(self):
        """Insert embeddings and search."""
        from app.rag.vector_store import get_vector_store
        from app.rag.embedding import get_embedding_provider

        store = get_vector_store(mode="real")
        provider = get_embedding_provider(mode="real")

        # Insert test vectors
        vec1 = await provider.embed_query("贵州茅台回购公告")
        await store.upsert(
            chunk_id=f"test_search_{uuid.uuid4().hex[:8]}",
            document_id="test_doc_1",
            vector=vec1,
            content="贵州茅台关于回购的公告",
            metadata={"symbol": "600519.SH", "document_type": "ANNOUNCEMENT", "model": provider.model_name},
        )

        # Search
        query_vec = await provider.embed_query("茅台最近有什么公告？")
        results = await store.similarity_search(query_vec, top_k=5, symbol="600519.SH")

        assert len(results) > 0
        assert results[0].score > 0.5  # Should be reasonably similar
