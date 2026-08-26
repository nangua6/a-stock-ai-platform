"""
Integration tests for AkShare data pipeline.

These tests require:
- Real network access (not Codex sandbox)
- AkShare installed in backend/.venv
- Eastmoney/SSE endpoints reachable

Run manually:
    cd backend && source .venv/bin/activate
    pytest tests/integration/ -v -m integration

DO NOT run in CI or sandbox – these will fail without network.
"""
import os
import pytest

# Ensure no proxy interference on macOS with Clash TUN
os.environ.setdefault("NO_PROXY", "*")

from app.market.akshare_provider import AkShareProvider
from app.market.provider_manager import ProviderManager
from app.market.mock_provider import MockMarketDataProvider
from app.market.cache import MarketDataCache
from app.market.base import DataFreshness

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def ak_provider():
    return AkShareProvider()


@pytest.fixture
def provider_manager():
    cache = MarketDataCache()
    return ProviderManager(
        providers=[AkShareProvider(), MockMarketDataProvider()],
        cache=cache,
    )


class TestAkShareProviderIntegration:
    """Test AkShareProvider against real Eastmoney API."""

    @pytest.mark.asyncio
    async def test_get_realtime_quote_returns_valid_data(self, ak_provider):
        """Quote must have non-empty symbol, positive price, valid source."""
        quote = await ak_provider.get_realtime_quote("600519.SH")
        assert quote.symbol == "600519.SH"
        assert quote.name != ""
        assert quote.price > 0
        assert quote.data_source == "akshare"
        assert quote.timestamp != ""

    @pytest.mark.asyncio
    async def test_get_kline_returns_bars(self, ak_provider):
        """K-line must return non-empty list with valid OHLCV."""
        klines = await ak_provider.get_kline("600519.SH", limit=30)
        assert len(klines) > 0
        for k in klines[:5]:
            assert k.symbol == "600519.SH"
            assert k.high >= k.low
            assert k.volume >= 0
            assert k.data_source == "akshare"
            assert k.trade_date != ""

    @pytest.mark.asyncio
    async def test_get_financial_data(self, ak_provider):
        """Financial data must have valid symbol and source."""
        fin = await ak_provider.get_financial_data("600519.SH")
        assert fin.symbol == "600519.SH"
        assert fin.data_source == "akshare"

    @pytest.mark.asyncio
    async def test_get_stock_list(self, ak_provider):
        """Stock list must return non-empty with valid structure."""
        stocks = await ak_provider.get_stock_list()
        assert len(stocks) > 100  # A-share has thousands of stocks
        first = stocks[0]
        assert "symbol" in first
        assert "name" in first
        assert "market" in first
        assert "." in first["symbol"]  # e.g. 600519.SH


class TestProviderManagerIntegration:
    """Test ProviderManager with real AkShare + Mock fallback."""

    @pytest.mark.asyncio
    async def test_quote_from_real_provider(self, provider_manager):
        """Manager should return data from AkShare (primary)."""
        quote = await provider_manager.get_realtime_quote("600519.SH")
        assert quote.price > 0
        assert quote.data_source == "akshare"

    @pytest.mark.asyncio
    async def test_fallback_to_mock_on_failure(self):
        """When AkShare fails, manager should fall back to Mock."""
        from app.market.akshare_provider import AkShareProvider

        class AlwaysFailProvider(AkShareProvider):
            @property
            def name(self):
                return "always_fail"

            async def get_realtime_quote(self, symbol):
                raise ConnectionError("Simulated failure")

        cache = MarketDataCache()
        manager = ProviderManager(
            providers=[AlwaysFailProvider(), MockMarketDataProvider()],
            cache=cache,
        )
        quote = await manager.get_realtime_quote("600519.SH")
        assert quote.price > 0
        assert quote.data_source == "mock"

    @pytest.mark.asyncio
    async def test_provider_status_tracking(self, provider_manager):
        """Provider status should track success/failure counts."""
        await provider_manager.get_realtime_quote("600519.SH")
        status = provider_manager.get_provider_status()
        assert len(status) >= 1
        ak_status = next(s for s in status if s["provider"] == "akshare")
        assert ak_status["total_requests"] >= 1

    @pytest.mark.asyncio
    async def test_quote_with_availability(self, provider_manager):
        """Quote with availability must include freshness metadata."""
        quote, avail = await provider_manager.get_quote_with_availability("600519.SH")
        assert quote.price > 0
        assert avail.is_available
        assert avail.freshness == DataFreshness.FRESH
        assert avail.provider == "akshare"
        assert avail.data_age_seconds == 0.0


class TestAkShareDataQuality:
    """Validate data quality from real AkShare."""

    @pytest.mark.asyncio
    async def test_quote_price_range(self, ak_provider):
        """Price must be within A-share daily limit (±20%)."""
        quote = await ak_provider.get_realtime_quote("600519.SH")
        if quote.pre_close > 0:
            limit = quote.pre_close * 0.20
            assert abs(quote.price - quote.pre_close) <= limit * 1.01  # 1% tolerance

    @pytest.mark.asyncio
    async def test_kline_date_continuity(self, ak_provider):
        """K-line dates should be sequential."""
        klines = await ak_provider.get_kline("600519.SH", limit=10)
        if len(klines) >= 2:
            dates = [k.trade_date for k in klines]
            assert dates == sorted(dates)
