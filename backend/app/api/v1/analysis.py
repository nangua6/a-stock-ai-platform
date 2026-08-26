"""AI analysis endpoints – uses MarketContextBuilder for structured data."""
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
from app.market.provider_manager import ProviderManager
from app.market.mock_provider import MockMarketDataProvider
from app.market.cache import MarketDataCache
from app.services.market_context_builder import MarketContextBuilder
from app.services.screening_engine import ScreeningEngine, ScreeningRule, FactorDirection

router = APIRouter()

# Wire up with ProviderManager
_cache = MarketDataCache()
_provider = ProviderManager(providers=[MockMarketDataProvider()], cache=_cache)
_context_builder = MarketContextBuilder(provider=_provider)
_screening_engine = ScreeningEngine()

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


class ScreeningRequest(BaseModel):
    criteria: str = "趋势最强"
    market: Optional[str] = None
    top_n: int = 10


@router.post("/stock")
async def analyze_stock(request: StockAnalysisRequest):
    """Full multi-dimensional stock analysis using AI agents."""
    # Build structured context
    snapshot = await _context_builder.build_stock_snapshot(request.symbol)
    ai_context = _context_builder.snapshot_to_ai_context(snapshot)

    # Include additional data for agents
    money_flow = await _provider.get_money_flow(request.symbol)
    news = await _provider.get_news(request.symbol)

    market_data = {
        **ai_context,
        "money_flow": money_flow,
        "news": news,
    }

    result = await _chief.analyze_stock(request.symbol, market_data)
    return {"success": True, "data": result}


@router.post("/market")
async def analyze_market():
    """Market-level analysis."""
    overview = await _provider.get_market_overview()
    result = await _chief.analyze_market(overview)
    return {"success": True, "data": result}


@router.post("/query")
async def natural_language_query(request: AnalysisRequest):
    """Natural language query – dispatches to appropriate agents."""
    context = {}
    if request.symbol:
        snapshot = await _context_builder.build_stock_snapshot(request.symbol)
        context = _context_builder.snapshot_to_ai_context(snapshot)

    response = await _chief.think(request.query, context)
    return {"success": True, "data": {"query": request.query, "response": response}}


@router.post("/candidates")
async def find_candidates(request: ScreeningRequest):
    """Find candidate stocks based on structured screening criteria."""
    stock_list = await _provider.get_stock_list()

    # Build candidate data
    candidates = []
    for stock in stock_list[:50]:  # Limit to prevent timeout
        sym = stock["symbol"]
        try:
            quote = await _provider.get_realtime_quote(sym)
            klines = await _provider.get_kline(sym, limit=60)
            candidates.append({
                "symbol": sym,
                "name": stock.get("name", ""),
                "quote": quote,
                "klines": klines,
            })
        except Exception:
            continue

    # Apply default screening rules based on criteria
    rules = _build_rules_for_criteria(request.criteria)
    result = _screening_engine.screen(candidates, rules, top_n=request.top_n)

    return {
        "success": True,
        "data": {
            "criteria": request.criteria,
            "total_screened": result.total_screened,
            "total_passed": result.total_passed,
            "candidates": [
                {
                    "symbol": c.symbol,
                    "name": c.name,
                    "score": c.score,
                    "factors": c.factors,
                    "matched_rules": c.matched_rules,
                }
                for c in result.candidates
            ],
        },
    }


def _build_rules_for_criteria(criteria: str) -> list:
    """Map natural language criteria to structured screening rules."""
    if "趋势" in criteria:
        return [
            ScreeningRule(name="ma_trend_up", factor="ma_trend", min_value=1.0, weight=3.0),
            ScreeningRule(name="positive_momentum", factor="momentum_5d", min_value=0.0, weight=2.0),
            ScreeningRule(name="volume_active", factor="volume_ratio", min_value=1.0, weight=1.0),
        ]
    elif "超卖" in criteria or "低位" in criteria:
        return [
            ScreeningRule(name="rsi_oversold", factor="rsi", max_value=35.0, direction=FactorDirection.LOWER, weight=3.0),
        ]
    elif "放量" in criteria:
        return [
            ScreeningRule(name="high_volume_ratio", factor="volume_ratio", min_value=2.0, weight=3.0),
            ScreeningRule(name="positive_change", factor="change_pct", min_value=0.0, weight=1.0),
        ]
    else:
        # Default: balanced
        return [
            ScreeningRule(name="reasonable_rsi", factor="rsi", min_value=30.0, max_value=70.0, weight=1.0),
            ScreeningRule(name="positive_momentum", factor="momentum_5d", min_value=-5.0, weight=1.0),
        ]
