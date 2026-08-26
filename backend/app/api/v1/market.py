"""Market data endpoints – powered by ProviderManager with fallback."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.market.provider_manager import ProviderManager
from app.market.mock_provider import MockMarketDataProvider
from app.market.cache import MarketDataCache
from app.services.technical_analysis import TechnicalAnalysisService

router = APIRouter()

# Provider manager: Mock only in sandbox, AkShare + Mock when network available
_cache = MarketDataCache()
_provider = ProviderManager(
    providers=[MockMarketDataProvider()],
    cache=_cache,
)
_ta_service = TechnicalAnalysisService()


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get real-time quote for a stock."""
    quote = await _provider.get_realtime_quote(symbol)
    return {"success": True, "data": quote.__dict__}


@router.get("/quotes")
async def get_quotes(symbols: str = Query(..., description="Comma-separated symbols")):
    """Batch get real-time quotes."""
    sym_list = [s.strip() for s in symbols.split(",")]
    quotes = await _provider.get_realtime_quotes(sym_list)
    return {"success": True, "data": [q.__dict__ for q in quotes]}


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    timeframe: str = Query("D", description="Timeframe: D, W, M"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get K-line data for a stock."""
    klines = await _provider.get_kline(symbol, timeframe=timeframe, limit=limit)
    return {"success": True, "data": [k.__dict__ for k in klines]}


@router.get("/overview")
async def get_market_overview():
    """Get market overview (indices, breadth, sentiment)."""
    overview = await _provider.get_market_overview()
    return {"success": True, "data": overview}


@router.get("/stocks")
async def get_stock_list(market: Optional[str] = None):
    """Get list of all stocks."""
    stocks = await _provider.get_stock_list(market)
    return {"success": True, "data": stocks}


@router.get("/financial/{symbol}")
async def get_financial(symbol: str):
    """Get financial data for a stock."""
    data = await _provider.get_financial_data(symbol)
    return {"success": True, "data": data.__dict__}


@router.get("/money-flow/{symbol}")
async def get_money_flow(symbol: str):
    """Get capital flow data."""
    data = await _provider.get_money_flow(symbol)
    return {"success": True, "data": data}


@router.get("/news")
async def get_news(symbol: Optional[str] = None, limit: int = 20):
    """Get recent news."""
    data = await _provider.get_news(symbol, limit)
    return {"success": True, "data": data}


@router.get("/announcements")
async def get_announcements(symbol: Optional[str] = None, limit: int = 20):
    """Get recent announcements."""
    data = await _provider.get_announcements(symbol, limit)
    return {"success": True, "data": data}


@router.get("/data-status")
async def get_data_status():
    """Get market data provider health status."""
    return {
        "success": True,
        "data": {
            "providers": _provider.get_provider_status(),
            "cache": _cache.stats,
        },
    }


@router.get("/technical/{symbol}")
async def get_technical_indicators(symbol: str, limit: int = Query(60, ge=5, le=500)):
    """Get computed technical indicators for a stock."""
    klines = await _provider.get_kline(symbol, timeframe="D", limit=limit)
    if not klines or len(klines) < 5:
        return {"success": False, "message": f"Insufficient data for {symbol} ({len(klines)} bars, need ≥5)"}
    indicators = _ta_service.compute(klines)
    return {"success": True, "data": indicators.to_dict()}
