"""Tests for new repositories: SyncJob, TechnicalSnapshot, AnalysisSnapshot."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base
from app.models.sync_job import DataSyncJob
from app.models.technical_snapshot import TechnicalSnapshot
from app.models.analysis_snapshot import AnalysisSnapshot
from app.repositories.factory import RepositoryFactory


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
async def repos(db_session: AsyncSession) -> RepositoryFactory:
    return RepositoryFactory(db_session)


# ── SyncJob Repository ────────────────────────────────────────────────────

class TestSyncJobRepository:
    @pytest.mark.asyncio
    async def test_create_job(self, repos):
        job = await repos.sync_jobs.create({
            "job_id": "test_job_001",
            "job_type": "stock_list",
            "status": "RUNNING",
        })
        assert job.job_id == "test_job_001"
        assert job.status == "RUNNING"
        assert job.id is not None

    @pytest.mark.asyncio
    async def test_get_by_job_id(self, repos):
        await repos.sync_jobs.create({"job_id": "j1", "job_type": "kline", "status": "RUNNING"})
        found = await repos.sync_jobs.get_by_job_id("j1")
        assert found is not None
        assert found.job_id == "j1"

    @pytest.mark.asyncio
    async def test_get_by_job_id_not_found(self, repos):
        found = await repos.sync_jobs.get_by_job_id("nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_update_status(self, repos):
        await repos.sync_jobs.create({"job_id": "j2", "job_type": "kline", "status": "RUNNING"})
        updated = await repos.sync_jobs.update_status(
            "j2", "SUCCESS", success_count=10, failed_count=0
        )
        assert updated is not None
        assert updated.status == "SUCCESS"
        assert updated.success_count == 10

    @pytest.mark.asyncio
    async def test_get_running_jobs(self, repos):
        await repos.sync_jobs.create({"job_id": "r1", "job_type": "kline", "status": "RUNNING"})
        await repos.sync_jobs.create({"job_id": "r2", "job_type": "kline", "status": "SUCCESS"})
        running = await repos.sync_jobs.get_running_jobs()
        assert len(running) == 1
        assert running[0].job_id == "r1"

    @pytest.mark.asyncio
    async def test_get_recent(self, repos):
        for i in range(5):
            await repos.sync_jobs.create({"job_id": f"j{i}", "job_type": "kline", "status": "SUCCESS"})
        recent = await repos.sync_jobs.get_recent(limit=3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_get_recent_by_type(self, repos):
        await repos.sync_jobs.create({"job_id": "a1", "job_type": "stock_list", "status": "SUCCESS"})
        await repos.sync_jobs.create({"job_id": "a2", "job_type": "kline", "status": "SUCCESS"})
        recent = await repos.sync_jobs.get_recent(job_type="stock_list")
        assert len(recent) == 1
        assert recent[0].job_type == "stock_list"


# ── TechnicalSnapshot Repository ──────────────────────────────────────────

class TestTechnicalSnapshotRepository:
    @pytest.mark.asyncio
    async def test_create_snapshot(self, repos):
        snap = await repos.technical_snapshots.create({
            "symbol": "600519.SH",
            "trade_date": "2024-01-15",
            "ma5": 1450.0,
            "rsi": 55.0,
            "data_source": "akshare",
        })
        assert snap.symbol == "600519.SH"
        assert snap.ma5 == 1450.0

    @pytest.mark.asyncio
    async def test_get_latest(self, repos):
        await repos.technical_snapshots.create({
            "symbol": "600519.SH", "trade_date": "2024-01-14", "ma5": 1440.0,
        })
        await repos.technical_snapshots.create({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "ma5": 1450.0,
        })
        latest = await repos.technical_snapshots.get_latest("600519.SH")
        assert latest is not None
        assert latest.trade_date == "2024-01-15"

    @pytest.mark.asyncio
    async def test_upsert_create(self, repos):
        snap = await repos.technical_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "ma5": 1450.0,
        })
        assert snap.ma5 == 1450.0

    @pytest.mark.asyncio
    async def test_upsert_update(self, repos):
        await repos.technical_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "ma5": 1450.0,
        })
        updated = await repos.technical_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "ma5": 1460.0,
        })
        assert updated.ma5 == 1460.0
        # Verify no duplicate
        count = await repos.technical_snapshots.count(symbol="600519.SH")
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_by_date(self, repos):
        await repos.technical_snapshots.create({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "ma5": 1450.0,
        })
        found = await repos.technical_snapshots.get_by_date("600519.SH", "2024-01-15")
        assert found is not None
        not_found = await repos.technical_snapshots.get_by_date("600519.SH", "2024-01-16")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_get_history(self, repos):
        for i in range(5):
            await repos.technical_snapshots.create({
                "symbol": "600519.SH", "trade_date": f"2024-01-{10+i:02d}", "ma5": 1440.0 + i,
            })
        history = await repos.technical_snapshots.get_history("600519.SH", limit=3)
        assert len(history) == 3


# ── AnalysisSnapshot Repository ───────────────────────────────────────────

class TestAnalysisSnapshotRepository:
    @pytest.mark.asyncio
    async def test_create_snapshot(self, repos):
        snap = await repos.analysis_snapshots.create({
            "symbol": "600519.SH",
            "name": "贵州茅台",
            "trade_date": "2024-01-15",
            "technical_score": 75.0,
            "recommendation": "BUY_CANDIDATE",
        })
        assert snap.symbol == "600519.SH"
        assert snap.recommendation == "BUY_CANDIDATE"

    @pytest.mark.asyncio
    async def test_get_latest(self, repos):
        await repos.analysis_snapshots.create({
            "symbol": "600519.SH", "trade_date": "2024-01-14", "recommendation": "WATCH",
        })
        await repos.analysis_snapshots.create({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "recommendation": "BUY_CANDIDATE",
        })
        latest = await repos.analysis_snapshots.get_latest("600519.SH")
        assert latest is not None
        assert latest.trade_date == "2024-01-15"

    @pytest.mark.asyncio
    async def test_upsert_create(self, repos):
        snap = await repos.analysis_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "recommendation": "HOLD",
        })
        assert snap.recommendation == "HOLD"

    @pytest.mark.asyncio
    async def test_upsert_update(self, repos):
        await repos.analysis_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "recommendation": "HOLD",
        })
        updated = await repos.analysis_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "recommendation": "BUY_CANDIDATE",
        })
        assert updated.recommendation == "BUY_CANDIDATE"
        count = await repos.analysis_snapshots.count(symbol="600519.SH")
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_by_recommendation(self, repos):
        await repos.analysis_snapshots.create({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "recommendation": "BUY_CANDIDATE",
        })
        await repos.analysis_snapshots.create({
            "symbol": "000001.SZ", "trade_date": "2024-01-15", "recommendation": "AVOID",
        })
        buys = await repos.analysis_snapshots.get_by_recommendation("BUY_CANDIDATE")
        assert len(buys) == 1
        assert buys[0].symbol == "600519.SH"


# ── Repository Factory ────────────────────────────────────────────────────

class TestRepositoryFactoryNewRepos:
    @pytest.mark.asyncio
    async def test_sync_jobs_property(self, repos):
        assert repos.sync_jobs is not None
        # Same instance on repeated access
        assert repos.sync_jobs is repos.sync_jobs

    @pytest.mark.asyncio
    async def test_technical_snapshots_property(self, repos):
        assert repos.technical_snapshots is not None
        assert repos.technical_snapshots is repos.technical_snapshots

    @pytest.mark.asyncio
    async def test_analysis_snapshots_property(self, repos):
        assert repos.analysis_snapshots is not None
        assert repos.analysis_snapshots is repos.analysis_snapshots
