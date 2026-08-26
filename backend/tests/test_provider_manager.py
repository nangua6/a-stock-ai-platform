"""Tests for ProviderManager (composite provider with fallback)."""
import pytest
from typing import List, Optional

from app.market.base import (
    MarketDataProvider,
    QuoteData,
    KlineData,
    FinancialData,
)
from app.market.provider_manager import ProviderManager
from app.market.cache import MarketDataCache


class FailingProvider(MarketDataProvider):
    """A provider that always fails."""
    @property
    def name(self):
        return "failing"

    async def get_realtime_quote(self, symbol):
        raise ConnectionError("DNS failure")

    async def get_realtime_quotes(self, symbols):
        raise ConnectionError("DNS failure")

    async def get_kline(self, symbol, timeframe="D", start_date=None, end_date=None, limit=100):
        raise ConnectionError("DNS failure")

    async def get_financial_data(self, symbol):
        raise ConnectionError("DNS failure")

    async def get_stock_list(self, market=None):
        raise ConnectionError("DNS failure")

    async def get_industry_stocks(self, industry_code):
        raise ConnectionError("DNS failure")

    async def get_market_overview(self):
        raise ConnectionError("DNS failure")

    async def get_money_flow(self, symbol):
        raise ConnectionError("DNS failure")

    async def get_news(self, symbol=None, limit=20):
        raise ConnectionError("DNS failure")

    async def get_announcements(self, symbol=None, limit=20):
        raise ConnectionError("DNS failure")


class TestProviderManager:
    def setup_method(self):
        self.cache = MarketDataCache()

    @pytest.mark.asyncio
    async def test_fallback_to_mock(self):
        """When primary fails, falls back to mock."""
        from app.market.mock_provider import MockMarketDataProvider
        manager = ProviderManager(
            providers=[FailingProvider(), MockMarketDataProvider()],
            cache=self.cache,
        )
        quote = await manager.get_realtime_quote("600519.SH")
        assert quote.price > 0
        assert quote.data_source == "mock"

    @pytest.mark.asyncio
    async def test_all_fail_returns_unavailable(self):
        """When all providers fail, returns empty/unavailable."""
        manager = ProviderManager(
            providers=[FailingProvider()],
            cache=self.cache,
        )
        quote = await manager.get_realtime_quote("600519.SH")
        assert quote.data_source == "unavailable"
        assert quote.price == 0.0

    @pytest.mark.asyncio
    async def test_caching(self):
        """Second call should hit cache."""
        from app.market.mock_provider import MockMarketDataProvider
        manager = ProviderManager(
            providers=[MockMarketDataProvider()],
            cache=self.cache,
        )
        q1 = await manager.get_realtime_quote("600519.SH")
        q2 = await manager.get_realtime_quote("600519.SH")
        # Both should succeed
        assert q1.symbol == q2.symbol
        # Cache should have been used
        assert self.cache.stats["hits"] >= 1

    @pytest.mark.asyncio
    async def test_provider_status_tracking(self):
        """Provider status should track failures."""
        from app.market.mock_provider import MockMarketDataProvider
        manager = ProviderManager(
            providers=[FailingProvider(), MockMarketDataProvider()],
            cache=self.cache,
        )
        await manager.get_realtime_quote("600519.SH")
        status = manager.get_provider_status()
        assert len(status) == 2
        # Failing provider should have recorded failure
        failing_status = next(s for s in status if s["provider"] == "failing")
        assert failing_status["consecutive_failures"] >= 1

    @pytest.mark.asyncio
    async def test_quote_with_availability(self):
        """get_quote_with_availability returns both data and metadata."""
        from app.market.mock_provider import MockMarketDataProvider
        manager = ProviderManager(
            providers=[MockMarketDataProvider()],
            cache=self.cache,
        )
        quote, availability = await manager.get_quote_with_availability("600519.SH")
        assert quote.price > 0
        assert availability.is_available
        assert availability.provider == "mock"

    @pytest.mark.asyncio
    async def test_kline_fallback(self):
        """K-line data falls back through provider chain."""
        from app.market.mock_provider import MockMarketDataProvider
        manager = ProviderManager(
            providers=[FailingProvider(), MockMarketDataProvider()],
            cache=self.cache,
        )
        klines = await manager.get_kline("600519.SH", limit=10)
        assert len(klines) == 10

    @pytest.mark.asyncio
    async def test_requires_at_least_one_provider(self):
        with pytest.raises(ValueError):
            ProviderManager(providers=[], cache=self.cache)
