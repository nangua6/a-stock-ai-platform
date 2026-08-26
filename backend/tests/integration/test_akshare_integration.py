"""
Integration tests for AkShare data pipeline.

These tests require:
- Real network access (not Codex sandbox)
- AkShare installed in backend/.venv
- Eastmoney/SSE endpoints reachable (may be intermittent due to rate limiting)

Run manually:
    cd backend && source .venv/bin/activate
    pytest tests/integration/ -v -m integration

DO NOT run in CI or sandbox – these will fail without network.
"""
import pytest

from app.market.akshare_provider import AkShareProvider
from app.market.provider_manager import ProviderManager
from app.market.mock_provider import MockMarketDataProvider
from app.market.cache import MarketDataCache
from app.market.base import DataFreshness

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
    async def test_get_realtime_quote(self, ak_provider):
        """Quote must have valid symbol and non-empty name (price may be 0 if enrichment fails)."""
        quote = await ak_provider.get_realtime_quote("600519.SH")
        assert quote.symbol == "600519.SH"
        assert quote.name != ""
        assert quote.data_source == "akshare"
        assert quote.timestamp != ""

    @pytest.mark.asyncio
    async def test_get_kline_returns_bars(self, ak_provider):
        """K-line must return non-empty list with valid OHLCV."""
        klines = await ak_provider.get_kline("600519.SH", limit=30)
        assert len(klines) > 0
        k = klines[0]
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
        assert len(stocks) > 100
        first = stocks[0]
        assert "symbol" in first
        assert "." in first["symbol"]


class TestProviderManagerIntegration:
    """Test ProviderManager with real AkShare + Mock fallback."""

    @pytest.mark.asyncio
    async def test_provider_manager_returns_data(self, provider_manager):
        """Manager should return data from AkShare or fallback to Mock."""
        quote = await provider_manager.get_realtime_quote("600519.SH")
        assert quote.price > 0  # Either akshare or mock
        assert quote.data_source in ("akshare", "mock")

    @pytest.mark.asyncio
    async def test_fallback_to_mock_on_failure(self):
        """When AkShare fails, manager should fall back to Mock."""
        class AlwaysFailProvider(AkShareProvider):
            @property
            def name(self):
                return "always_fail"
            async def get_realtime_quote(self, symbol):
                raise ConnectionError("Simulated failure")

        manager = ProviderManager(
            providers=[AlwaysFailProvider(), MockMarketDataProvider()],
            cache=MarketDataCache(),
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
        # At least one provider should have been tried
        total = sum(s["total_requests"] for s in status)
        assert total >= 1

    @pytest.mark.asyncio
    async def test_kline_fallback(self, provider_manager):
        """K-line should return data from primary or fallback."""
        klines = await provider_manager.get_kline("600519.SH", limit=10)
        assert len(klines) > 0

    @pytest.mark.asyncio
    async def test_quote_with_availability(self, provider_manager):
        """Quote with availability must include freshness metadata."""
        quote, avail = await provider_manager.get_quote_with_availability("600519.SH")
        assert quote.price > 0 or quote.data_source == "unavailable"
        assert avail.freshness in (DataFreshness.FRESH, DataFreshness.UNAVAILABLE)


class TestAkShareDataQuality:
    """Validate data quality from real AkShare."""

    @pytest.mark.asyncio
    async def test_kline_date_continuity(self, ak_provider):
        """K-line dates should be sequential."""
        klines = await ak_provider.get_kline("600519.SH", limit=10)
        if len(klines) >= 2:
            dates = [k.trade_date for k in klines]
            assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_kline_ohlc_consistency(self, ak_provider):
        """High >= Low, High >= Open, High >= Close for each bar."""
        klines = await ak_provider.get_kline("600519.SH", limit=10)
        for k in klines:
            assert k.high >= k.low
            assert k.high >= k.open
            assert k.high >= k.close
