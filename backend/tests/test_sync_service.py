"""Tests for SyncService using MockProvider and in-memory SQLite."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base
from app.market.mock_provider import MockMarketDataProvider
from app.repositories.factory import RepositoryFactory
from app.services.sync_service import SyncService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
def provider():
    return MockMarketDataProvider()


@pytest_asyncio.fixture
async def sync_service(db_session: AsyncSession, provider) -> SyncService:
    return SyncService(db_session, provider)


class TestSyncServiceJobManagement:
    @pytest.mark.asyncio
    async def test_sync_stock_list_creates_job(self, sync_service):
        result = await sync_service.sync_stock_list()
        assert "job_id" in result
        assert result["status"] == "SUCCESS"
        assert result["count"] > 0

    @pytest.mark.asyncio
    async def test_sync_stock_list_persists_data(self, sync_service):
        await sync_service.sync_stock_list()
        count = await sync_service.repos.stocks.count()
        assert count > 0

    @pytest.mark.asyncio
    async def test_sync_stock_list_job_recorded(self, sync_service):
        result = await sync_service.sync_stock_list()
        job = await sync_service.repos.sync_jobs.get_by_job_id(result["job_id"])
        assert job is not None
        assert job.status == "SUCCESS"
        assert job.success_count > 0


class TestSyncServiceKlines:
    @pytest.mark.asyncio
    async def test_sync_klines_single_symbol(self, sync_service):
        result = await sync_service.sync_klines(["600519.SH"])
        assert result["status"] == "SUCCESS"
        assert result["success"] == 1

    @pytest.mark.asyncio
    async def test_sync_klines_persists_to_db(self, sync_service):
        await sync_service.sync_klines(["600519.SH"])
        klines = await sync_service.repos.klines.get_by_symbol("600519.SH", limit=10)
        assert len(klines) > 0

    @pytest.mark.asyncio
    async def test_sync_klines_multiple_symbols(self, sync_service):
        result = await sync_service.sync_klines(["600519.SH", "000001.SZ"])
        assert result["success"] == 2

    @pytest.mark.asyncio
    async def test_sync_klines_graceful_failure(self, sync_service):
        # One valid, one that might fail gracefully
        result = await sync_service.sync_klines(["600519.SH", "INVALID.XX"])
        # Should succeed for at least one
        assert result["success"] >= 1

    @pytest.mark.asyncio
    async def test_sync_klines_idempotent(self, sync_service):
        """Running sync twice should not create duplicates."""
        await sync_service.sync_klines(["600519.SH"])
        count1 = len(await sync_service.repos.klines.get_by_symbol("600519.SH", limit=200))
        await sync_service.sync_klines(["600519.SH"])
        count2 = len(await sync_service.repos.klines.get_by_symbol("600519.SH", limit=200))
        assert count1 == count2


class TestSyncServiceTechnical:
    @pytest.mark.asyncio
    async def test_compute_technical_snapshots(self, sync_service):
        # First sync klines
        await sync_service.sync_klines(["600519.SH"], limit=120)
        result = await sync_service.compute_technical_snapshots(["600519.SH"])
        assert result["success"] == 1

    @pytest.mark.asyncio
    async def test_technical_snapshot_persisted(self, sync_service):
        await sync_service.sync_klines(["600519.SH"], limit=120)
        await sync_service.compute_technical_snapshots(["600519.SH"])
        snap = await sync_service.repos.technical_snapshots.get_latest("600519.SH")
        assert snap is not None
        assert snap.symbol == "600519.SH"
        assert snap.ma5 > 0 or snap.rsi > 0  # At least some indicators computed


class TestSyncServiceAnalysis:
    @pytest.mark.asyncio
    async def test_compute_analysis_snapshots(self, sync_service):
        await sync_service.sync_klines(["600519.SH"], limit=120)
        result = await sync_service.compute_analysis_snapshots(["600519.SH"])
        assert result["success"] == 1

    @pytest.mark.asyncio
    async def test_analysis_snapshot_persisted(self, sync_service):
        await sync_service.sync_klines(["600519.SH"], limit=120)
        await sync_service.compute_analysis_snapshots(["600519.SH"])
        snap = await sync_service.repos.analysis_snapshots.get_latest("600519.SH")
        assert snap is not None
        assert snap.recommendation in [
            "WATCH", "BUY_CANDIDATE", "HOLD", "REDUCE", "AVOID", "DATA_UNAVAILABLE"
        ]


class TestSyncServiceFull:
    @pytest.mark.asyncio
    async def test_sync_full(self, sync_service):
        result = await sync_service.sync_full(["600519.SH", "000001.SZ"])
        assert "stock_list" in result
        assert "klines" in result
        assert "technical" in result
        assert "analysis" in result
        assert result["stock_list"]["status"] == "SUCCESS"


class TestSyncServiceStatus:
    @pytest.mark.asyncio
    async def test_get_sync_status(self, sync_service):
        await sync_service.sync_stock_list()
        status = await sync_service.get_sync_status()
        assert "running_jobs" in status
        assert "recent_jobs" in status
        assert len(status["recent_jobs"]) > 0

    @pytest.mark.asyncio
    async def test_get_sync_history(self, sync_service):
        await sync_service.sync_stock_list()
        history = await sync_service.get_sync_history()
        assert len(history) > 0
        assert "job_id" in history[0]
