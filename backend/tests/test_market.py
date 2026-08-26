"""Tests for market data providers."""
import pytest
from app.market.mock_provider import MockMarketDataProvider


@pytest.mark.asyncio
async def test_mock_quote():
    provider = MockMarketDataProvider()
    quote = await provider.get_realtime_quote("600519.SH")
    assert quote.symbol == "600519.SH"
    assert quote.name == "贵州茅台"
    assert quote.price > 0


@pytest.mark.asyncio
async def test_mock_kline():
    provider = MockMarketDataProvider()
    klines = await provider.get_kline("600519.SH", limit=50)
    assert len(klines) == 50
    for k in klines:
        assert k.high >= k.low
        assert k.volume > 0


@pytest.mark.asyncio
async def test_mock_market_overview():
    provider = MockMarketDataProvider()
    overview = await provider.get_market_overview()
    assert "indices" in overview
    assert "上证指数" in overview["indices"]
