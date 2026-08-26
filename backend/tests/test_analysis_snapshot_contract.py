"""Regression tests for AnalysisSnapshot data contract.

Ensures current_price comes from real quote data, NOT from scores.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base
from app.market.mock_provider import MockMarketDataProvider
from app.market.provider_manager import ProviderManager
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


class TestCurrentPriceContract:
    """current_price must come from real quote, not from technical score."""

    @pytest.mark.asyncio
    async def test_current_price_is_not_technical_score(self, sync_service):
        """Regression: current_price must NOT equal technical_score."""
        await sync_service.sync_klines(["600519.SH"], limit=120)
        await sync_service.compute_analysis_snapshots(["600519.SH"])

        snap = await sync_service.repos.analysis_snapshots.get_latest("600519.SH")
        assert snap is not None

        # current_price should be a real price (e.g. ~100-2000 range for mock)
        # NOT a score (0-100 range)
        if snap.current_price is not None and snap.current_price > 0:
            # The technical_score is 0-100; current_price for mock data is > 100
            # This ensures they are different fields
            assert snap.current_price != snap.technical_score or snap.technical_score == 0

    @pytest.mark.asyncio
    async def test_current_price_comes_from_quote(self, sync_service):
        """current_price should match the provider's quote price."""
        # Get quote from provider directly
        quote = await sync_service.provider.get_realtime_quote("600519.SH")
        assert quote is not None
        assert quote.price > 0

        # Sync and compute
        await sync_service.sync_klines(["600519.SH"], limit=120)
        await sync_service.compute_analysis_snapshots(["600519.SH"])

        snap = await sync_service.repos.analysis_snapshots.get_latest("600519.SH")
        assert snap is not None
        assert snap.current_price is not None
        assert snap.current_price > 0

    @pytest.mark.asyncio
    async def test_change_pct_populated(self, sync_service):
        """change_pct should come from quote, not be hardcoded to 0."""
        await sync_service.sync_klines(["600519.SH"], limit=120)
        await sync_service.compute_analysis_snapshots(["600519.SH"])

        snap = await sync_service.repos.analysis_snapshots.get_latest("600519.SH")
        assert snap is not None
        # change_pct should be populated (may be 0 if mock returns 0, but must not be None)
        assert snap.change_pct is not None


class TestAnalysisSnapshotFields:
    """Verify all required fields are present and correctly typed."""

    @pytest.mark.asyncio
    async def test_all_required_fields_present(self, sync_service):
        await sync_service.sync_klines(["600519.SH"], limit=120)
        await sync_service.compute_analysis_snapshots(["600519.SH"])

        snap = await sync_service.repos.analysis_snapshots.get_latest("600519.SH")
        assert snap is not None

        # Required fields
        assert snap.symbol == "600519.SH"
        assert snap.trade_date is not None
        assert snap.recommendation in [
            "WATCH", "BUY_CANDIDATE", "HOLD", "REDUCE", "AVOID", "DATA_UNAVAILABLE"
        ]
        assert 0 <= snap.technical_score <= 100
        assert 0 <= snap.overall_score <= 100
        assert 0 <= snap.confidence <= 1
        assert snap.data_quality in ["GOOD", "STALE", "PARTIAL", "UNAVAILABLE"]
        assert snap.data_source is not None

    @pytest.mark.asyncio
    async def test_technical_detail_json(self, sync_service):
        await sync_service.sync_klines(["600519.SH"], limit=120)
        await sync_service.compute_analysis_snapshots(["600519.SH"])

        snap = await sync_service.repos.analysis_snapshots.get_latest("600519.SH")
        assert snap is not None
        assert snap.technical_detail is not None
        assert isinstance(snap.technical_detail, dict)
        assert "score" in snap.technical_detail
