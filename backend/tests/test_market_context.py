"""Tests for MarketContextBuilder."""
import pytest
from app.services.market_context_builder import MarketContextBuilder, UNAVAILABLE
from app.market.provider_manager import ProviderManager
from app.market.mock_provider import MockMarketDataProvider
from app.market.cache import MarketDataCache


class TestMarketContextBuilder:
    def setup_method(self):
        cache = MarketDataCache()
        provider = ProviderManager(providers=[MockMarketDataProvider()], cache=cache)
        self.builder = MarketContextBuilder(provider=provider)

    @pytest.mark.asyncio
    async def test_build_snapshot(self):
        snapshot = await self.builder.build_stock_snapshot("600519.SH")
        assert snapshot.symbol == "600519.SH"
        assert snapshot.current_price > 0
        assert snapshot.data_quality.is_available

    @pytest.mark.asyncio
    async def test_snapshot_to_ai_context(self):
        snapshot = await self.builder.build_stock_snapshot("600519.SH")
        ctx = self.builder.snapshot_to_ai_context(snapshot)
        assert ctx["symbol"] == "600519.SH"
        assert "quote" in ctx
        assert "technicals" in ctx
        assert "data_quality" in ctx

    @pytest.mark.asyncio
    async def test_ai_context_has_technicals(self):
        snapshot = await self.builder.build_stock_snapshot("600519.SH")
        ctx = self.builder.snapshot_to_ai_context(snapshot)
        if ctx["technicals"] != UNAVAILABLE:
            assert "ma5" in ctx["technicals"]
            assert "rsi" in ctx["technicals"]

    @pytest.mark.asyncio
    async def test_ai_context_data_quality(self):
        snapshot = await self.builder.build_stock_snapshot("600519.SH")
        ctx = self.builder.snapshot_to_ai_context(snapshot)
        dq = ctx["data_quality"]
        assert "is_available" in dq
        assert "freshness" in dq
        assert "provider" in dq

    @pytest.mark.asyncio
    async def test_build_market_context(self):
        ctx = await self.builder.build_market_context()
        assert "market_overview" in ctx
        assert "timestamp" in ctx
