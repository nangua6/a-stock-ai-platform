"""PostgreSQL integration tests.

These tests require a running PostgreSQL instance.
Run with: pytest tests/integration/test_postgres_persistence.py -v -m integration

Requires: docker compose up -d postgres
"""
from __future__ import annotations

import os
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base
from app.models import (
    User, Account, Stock, Kline, Order, Trade, Position, Signal,
    DataSyncJob, TechnicalSnapshot, AnalysisSnapshot,
)
from app.repositories.factory import RepositoryFactory
from app.services.sync_service import SyncService
from app.services.data_quality import DataQualityService
from app.market.mock_provider import MockMarketDataProvider


# Skip if no PostgreSQL available
POSTGRES_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/astock_ai",
)

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def pg_session():
    """Create a PostgreSQL session for integration testing."""
    try:
        engine = create_async_engine(POSTGRES_URL, echo=False)
        # Test connection
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
    except Exception:
        pytest.skip("PostgreSQL not available")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    # Cleanup: drop all test tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def repos(pg_session: AsyncSession) -> RepositoryFactory:
    return RepositoryFactory(pg_session)


# ── Connection Tests ──────────────────────────────────────────────────────

class TestPostgresConnection:
    @pytest.mark.asyncio
    async def test_connection(self, pg_session):
        """Verify PostgreSQL connection works."""
        result = await pg_session.execute(
            __import__("sqlalchemy").text("SELECT 1 as num")
        )
        row = result.fetchone()
        assert row[0] == 1

    @pytest.mark.asyncio
    async def test_tables_created(self, pg_session):
        """Verify all tables exist after migration."""
        result = await pg_session.execute(
            __import__("sqlalchemy").text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
        )
        tables = {row[0] for row in result.fetchall()}
        expected = {
            "users", "accounts", "stocks", "klines", "orders", "trades",
            "positions", "signals", "data_sync_jobs", "technical_snapshots",
            "analysis_snapshots", "watchlist_items",
        }
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"


# ── CRUD Tests ────────────────────────────────────────────────────────────

class TestPostgresCRUD:
    @pytest.mark.asyncio
    async def test_insert_and_query(self, repos):
        """Basic insert and query."""
        user = await repos.users.create({
            "username": f"test_{uuid.uuid4().hex[:6]}",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
            "role": "RESEARCH",
        })
        assert user.id is not None
        found = await repos.users.get_by_id(user.id)
        assert found is not None
        assert found.username == user.username

    @pytest.mark.asyncio
    async def test_update(self, repos):
        """Update existing record."""
        user = await repos.users.create({
            "username": f"test_{uuid.uuid4().hex[:6]}",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        updated = await repos.users.update(user.id, {"full_name": "Test User"})
        assert updated.full_name == "Test User"

    @pytest.mark.asyncio
    async def test_delete(self, repos):
        """Delete record."""
        user = await repos.users.create({
            "username": f"test_{uuid.uuid4().hex[:6]}",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        deleted = await repos.users.delete_by_id(user.id)
        assert deleted is True
        found = await repos.users.get_by_id(user.id)
        assert found is None


# ── Kline Upsert Tests ───────────────────────────────────────────────────

class TestPostgresKlineUpsert:
    @pytest.mark.asyncio
    async def test_upsert_no_duplicate(self, repos):
        """Kline upsert should not create duplicates."""
        data = {
            "symbol": "600519.SH",
            "trade_date": "2024-01-15",
            "timeframe": "D",
            "open": 1440.0, "high": 1460.0, "low": 1430.0, "close": 1450.0,
            "volume": 100000, "amount": 145000000.0, "data_source": "test",
        }
        await repos.klines.bulk_upsert([data])
        await repos.klines.bulk_upsert([data])
        count = await repos.klines.count(symbol="600519.SH")
        assert count == 1

    @pytest.mark.asyncio
    async def test_upsert_updates(self, repos):
        """Upsert with same key should update."""
        data = {
            "symbol": "600519.SH", "trade_date": "2024-01-15", "timeframe": "D",
            "open": 1440.0, "high": 1460.0, "low": 1430.0, "close": 1450.0,
            "volume": 100000, "data_source": "test",
        }
        await repos.klines.bulk_upsert([data])
        await repos.klines.bulk_upsert([{**data, "close": 1480.0}])
        klines = await repos.klines.get_by_symbol("600519.SH", limit=10)
        assert len(klines) == 1
        assert klines[0].close == 1480.0

    @pytest.mark.asyncio
    async def test_different_dates_no_duplicate(self, repos):
        """Different dates should create separate records."""
        for date in ["2024-01-15", "2024-01-16"]:
            await repos.klines.bulk_upsert([{
                "symbol": "600519.SH", "trade_date": date, "timeframe": "D",
                "open": 100, "high": 110, "low": 90, "close": 105,
                "volume": 1000, "data_source": "test",
            }])
        count = await repos.klines.count(symbol="600519.SH")
        assert count == 2


# ── TechnicalSnapshot Tests ───────────────────────────────────────────────

class TestPostgresTechnicalSnapshot:
    @pytest.mark.asyncio
    async def test_upsert_no_duplicate(self, repos):
        await repos.technical_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "ma5": 1450.0,
        })
        await repos.technical_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15", "ma5": 1460.0,
        })
        count = await repos.technical_snapshots.count(symbol="600519.SH")
        assert count == 1
        snap = await repos.technical_snapshots.get_latest("600519.SH")
        assert snap.ma5 == 1460.0


# ── AnalysisSnapshot Tests ────────────────────────────────────────────────

class TestPostgresAnalysisSnapshot:
    @pytest.mark.asyncio
    async def test_upsert_no_duplicate(self, repos):
        await repos.analysis_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15",
            "current_price": 1450.0, "recommendation": "HOLD",
        })
        await repos.analysis_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15",
            "current_price": 1480.0, "recommendation": "BUY_CANDIDATE",
        })
        count = await repos.analysis_snapshots.count(symbol="600519.SH")
        assert count == 1
        snap = await repos.analysis_snapshots.get_latest("600519.SH")
        assert snap.recommendation == "BUY_CANDIDATE"
        assert snap.current_price == 1480.0

    @pytest.mark.asyncio
    async def test_current_price_from_quote(self, repos):
        """current_price must be a real price, not a score."""
        snap = await repos.analysis_snapshots.upsert({
            "symbol": "600519.SH", "trade_date": "2024-01-15",
            "current_price": 1450.0, "technical_score": 75.0,
        })
        # These must be different values
        assert snap.current_price != snap.technical_score


# ── SyncJob Tests ─────────────────────────────────────────────────────────

class TestPostgresSyncJob:
    @pytest.mark.asyncio
    async def test_sync_job_lifecycle(self, repos):
        job = await repos.sync_jobs.create({
            "job_id": f"test_{uuid.uuid4().hex[:6]}",
            "job_type": "kline",
            "status": "RUNNING",
        })
        assert job.status == "RUNNING"

        updated = await repos.sync_jobs.update_status(
            job.job_id, "SUCCESS", success_count=10
        )
        assert updated.status == "SUCCESS"
        assert updated.success_count == 10

    @pytest.mark.asyncio
    async def test_get_running_jobs(self, repos):
        jid = f"test_{uuid.uuid4().hex[:6]}"
        await repos.sync_jobs.create({
            "job_id": jid, "job_type": "kline", "status": "RUNNING",
        })
        running = await repos.sync_jobs.get_running_jobs()
        assert any(j.job_id == jid for j in running)


# ── Transaction Tests ─────────────────────────────────────────────────────

class TestPostgresTransaction:
    @pytest.mark.asyncio
    async def test_rollback_on_error(self, pg_session):
        """Transaction should rollback on error without losing committed data."""
        repos = RepositoryFactory(pg_session)
        user = await repos.users.create({
            "username": f"rollback_{uuid.uuid4().hex[:6]}",
            "email": f"rollback_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        await pg_session.commit()

        # Save id before rollback expires attributes
        user_id = user.id

        # Simulate error in a new transaction – duplicate unique field
        try:
            await repos.users.create({
                "username": user.username,  # Duplicate
                "email": f"other_{uuid.uuid4().hex[:6]}@example.com",
                "hashed_password": "hashed",
            })
            await pg_session.flush()
        except Exception:
            await pg_session.rollback()

        # Committed user should still exist
        found = await repos.users.get_by_id(user_id)
        assert found is not None


# ── Full Pipeline Test ────────────────────────────────────────────────────

class TestPostgresFullPipeline:
    @pytest.mark.asyncio
    async def test_sync_service_pipeline(self, pg_session):
        """Test full ProviderManager -> MarketDataService -> Repository -> DB."""
        provider = MockMarketDataProvider()
        svc = SyncService(pg_session, provider)

        # Sync stock list
        result = await svc.sync_stock_list()
        assert result["status"] == "SUCCESS"
        assert result["count"] > 0

        # Sync klines
        result = await svc.sync_klines(["600519.SH"])
        assert result["status"] == "SUCCESS"

        # Compute technical snapshots
        result = await svc.compute_technical_snapshots(["600519.SH"])
        assert result["status"] == "SUCCESS"

        # Compute analysis snapshots
        result = await svc.compute_analysis_snapshots(["600519.SH"])
        assert result["status"] == "SUCCESS"

        # Verify analysis snapshot has correct current_price
        repos = RepositoryFactory(pg_session)
        snap = await repos.analysis_snapshots.get_latest("600519.SH")
        assert snap is not None
        assert snap.current_price > 0  # Real price from mock provider
        assert snap.current_price != snap.technical_score  # Not a score

    @pytest.mark.asyncio
    async def test_idempotent_full_sync(self, pg_session):
        """Running full sync twice should not create duplicates."""
        provider = MockMarketDataProvider()
        svc = SyncService(pg_session, provider)

        await svc.sync_stock_list()
        await svc.sync_klines(["600519.SH"])
        count1 = len(await RepositoryFactory(pg_session).klines.get_by_symbol("600519.SH", limit=200))

        await svc.sync_klines(["600519.SH"])
        count2 = len(await RepositoryFactory(pg_session).klines.get_by_symbol("600519.SH", limit=200))

        assert count1 == count2


# ── Watchlist Tests ────────────────────────────────────────────────────────

class TestPostgresWatchlist:
    @pytest.mark.asyncio
    async def test_add_watchlist(self, repos):
        """Add a stock to watchlist."""
        user = await repos.users.create({
            "username": f"wl_{uuid.uuid4().hex[:6]}",
            "email": f"wl_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        item = await repos.watchlist.add_item(user.id, "600519.SH", "贵州茅台")
        assert item.symbol == "600519.SH"
        assert item.name == "贵州茅台"
        assert item.id is not None

    @pytest.mark.asyncio
    async def test_duplicate_add_idempotent(self, repos):
        """Adding same stock twice should return same record."""
        user = await repos.users.create({
            "username": f"wl_{uuid.uuid4().hex[:6]}",
            "email": f"wl_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        item1 = await repos.watchlist.add_item(user.id, "600519.SH")
        item2 = await repos.watchlist.add_item(user.id, "600519.SH")
        assert item1.id == item2.id

    @pytest.mark.asyncio
    async def test_remove_watchlist(self, repos):
        """Remove a stock from watchlist."""
        user = await repos.users.create({
            "username": f"wl_{uuid.uuid4().hex[:6]}",
            "email": f"wl_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        await repos.watchlist.add_item(user.id, "600519.SH")
        removed = await repos.watchlist.remove_item(user.id, "600519.SH")
        assert removed is True
        exists = await repos.watchlist.is_in_watchlist(user.id, "600519.SH")
        assert exists is False

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self, repos):
        """Removing non-existent stock should return False."""
        user = await repos.users.create({
            "username": f"wl_{uuid.uuid4().hex[:6]}",
            "email": f"wl_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        removed = await repos.watchlist.remove_item(user.id, "999999.SH")
        assert removed is False

    @pytest.mark.asyncio
    async def test_get_by_user(self, repos):
        """Get all watchlist items for a user."""
        user = await repos.users.create({
            "username": f"wl_{uuid.uuid4().hex[:6]}",
            "email": f"wl_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        await repos.watchlist.add_item(user.id, "600519.SH", "贵州茅台")
        await repos.watchlist.add_item(user.id, "000858.SZ", "五粮液")
        items = await repos.watchlist.get_by_user(user.id)
        assert len(items) == 2
        symbols = {i.symbol for i in items}
        assert "600519.SH" in symbols
        assert "000858.SZ" in symbols

    @pytest.mark.asyncio
    async def test_unique_constraint(self, repos):
        """Unique(user_id, symbol) prevents duplicates at DB level."""
        user = await repos.users.create({
            "username": f"wl_{uuid.uuid4().hex[:6]}",
            "email": f"wl_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        await repos.watchlist.add_item(user.id, "600519.SH")
        # Second add should not create duplicate
        await repos.watchlist.add_item(user.id, "600519.SH")
        items = await repos.watchlist.get_by_user(user.id)
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_different_users_independent(self, repos):
        """Different users can have same stock in watchlist."""
        user1 = await repos.users.create({
            "username": f"wl1_{uuid.uuid4().hex[:6]}",
            "email": f"wl1_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        user2 = await repos.users.create({
            "username": f"wl2_{uuid.uuid4().hex[:6]}",
            "email": f"wl2_{uuid.uuid4().hex[:6]}@example.com",
            "hashed_password": "hashed",
        })
        await repos.watchlist.add_item(user1.id, "600519.SH")
        await repos.watchlist.add_item(user2.id, "600519.SH")
        items1 = await repos.watchlist.get_by_user(user1.id)
        items2 = await repos.watchlist.get_by_user(user2.id)
        assert len(items1) == 1
        assert len(items2) == 1
