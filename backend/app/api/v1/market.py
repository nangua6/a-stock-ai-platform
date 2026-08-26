"""Market data endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.market.mock_provider import MockMarketDataProvider

router = APIRouter()
provider = MockMarketDataProvider()  # Will be injected via DI in production


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get real-time quote for a stock."""
    quote = await provider.get_realtime_quote(symbol)
    return {"success": True, "data": quote.__dict__}


@router.get("/quotes")
async def get_quotes(symbols: str = Query(..., description="Comma-separated symbols")):
    """Batch get real-time quotes."""
    sym_list = [s.strip() for s in symbols.split(",")]
    quotes = await provider.get_realtime_quotes(sym_list)
    return {"success": True, "data": [q.__dict__ for q in quotes]}


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    timeframe: str = Query("D", description="Timeframe: D, 1, 5, 15, 30, 60"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get K-line data for a stock."""
    klines = await provider.get_kline(symbol, timeframe=timeframe, limit=limit)
    return {"success": True, "data": [k.__dict__ for k in klines]}


@router.get("/overview")
async def get_market_overview():
    """Get market overview (indices, breadth, sentiment)."""
    overview = await provider.get_market_overview()
    return {"success": True, "data": overview}


@router.get("/stocks")
async def get_stock_list(market: Optional[str] = None):
    """Get list of all stocks."""
    stocks = await provider.get_stock_list(market)
    return {"success": True, "data": stocks}


@router.get("/financial/{symbol}")
async def get_financial(symbol: str):
    """Get financial data for a stock."""
    data = await provider.get_financial_data(symbol)
    return {"success": True, "data": data.__dict__}


@router.get("/money-flow/{symbol}")
async def get_money_flow(symbol: str):
    """Get capital flow data for a stock."""
    data = await provider.get_money_flow(symbol)
    return {"success": True, "data": data}


@router.get("/news")
async def get_news(symbol: Optional[str] = None, limit: int = 20):
    """Get recent news."""
    data = await provider.get_news(symbol, limit)
    return {"success": True, "data": data}


@router.get("/announcements")
async def get_announcements(symbol: Optional[str] = None, limit: int = 20):
    """Get recent announcements."""
    data = await provider.get_announcements(symbol, limit)
    return {"success": True, "data": data}
