"""AI analysis endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.agents.chief_agent import ChiefAgent
from app.agents.specialist_agents import (
    TechnicalAgent,
    FundamentalAgent,
    NewsAgent,
    SentimentAgent,
    RiskAgent,
)
from app.market.mock_provider import MockMarketDataProvider

router = APIRouter()

# Wire up agents
_market_provider = MockMarketDataProvider()
_chief = ChiefAgent(agents={
    "TechnicalAgent": TechnicalAgent(),
    "FundamentalAgent": FundamentalAgent(),
    "NewsAgent": NewsAgent(),
    "SentimentAgent": SentimentAgent(),
    "RiskAgent": RiskAgent(),
})


class AnalysisRequest(BaseModel):
    query: str
    symbol: Optional[str] = None


class StockAnalysisRequest(BaseModel):
    symbol: str


@router.post("/stock")
async def analyze_stock(request: StockAnalysisRequest):
    """Full multi-dimensional stock analysis using AI agents."""
    # Gather data
    quote = await _market_provider.get_realtime_quote(request.symbol)
    klines = await _market_provider.get_kline(request.symbol, limit=60)
    financial = await _market_provider.get_financial_data(request.symbol)
    news = await _market_provider.get_news(request.symbol)
    money_flow = await _market_provider.get_money_flow(request.symbol)

    market_data = {
        "quote": quote.__dict__,
        "klines": [k.__dict__ for k in klines[-10:]],  # Last 10 bars for context
        "financial": financial.__dict__,
        "news": news,
        "money_flow": money_flow,
    }

    result = await _chief.analyze_stock(request.symbol, market_data)
    return {"success": True, "data": result}


@router.post("/market")
async def analyze_market():
    """Market-level analysis."""
    overview = await _market_provider.get_market_overview()
    result = await _chief.analyze_market(overview)
    return {"success": True, "data": result}


@router.post("/query")
async def natural_language_query(request: AnalysisRequest):
    """Natural language query – dispatches to appropriate agents."""
    context = {}
    if request.symbol:
        quote = await _market_provider.get_realtime_quote(request.symbol)
        context["quote"] = quote.__dict__

    response = await _chief.think(request.query, context)
    return {"success": True, "data": {"query": request.query, "response": response}}


@router.get("/candidates")
async def find_candidates(criteria: str = "趋势最强"):
    """Find candidate stocks based on criteria."""
    stock_list = await _market_provider.get_stock_list()
    result = await _chief.find_candidates(criteria, stock_list)
    return {"success": True, "data": result}
