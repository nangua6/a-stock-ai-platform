"""
Built-in tools for the InvestmentResearchAgent.

Each tool wraps an existing service – never re-implements business logic.
Tools accept an optional provider for mode-aware data sourcing.
Tools are registered with the global ToolRegistry on import.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.tools.registry.base import Tool, ToolPermission, get_tool_registry

logger = get_logger("tools.builtin")


# ──────────────────────────────────────────────────────────────────────────────
# Helper: safe JSON serialiser for dataclass-like objects
# ──────────────────────────────────────────────────────────────────────────────

def _to_serializable(obj: Any) -> Any:
    """Convert dataclasses, enums, datetimes to JSON-safe primitives."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(v) for v in obj]
    return obj


# ──────────────────────────────────────────────────────────────────────────────
# Shared provider instance (set by register_builtin_tools)
# ──────────────────────────────────────────────────────────────────────────────

_shared_provider = None


def _get_provider():
    """Get or create the shared provider."""
    global _shared_provider
    if _shared_provider is None:
        from app.market.factory import create_provider
        _shared_provider = create_provider()
    return _shared_provider


# ══════════════════════════════════════════════════════════════════════════════
# Tool 1: MarketDataTool
# ══════════════════════════════════════════════════════════════════════════════

async def _market_data_handler(
    action: str,
    symbol: str = "",
    timeframe: str = "1d",
    limit: int = 120,
) -> dict:
    """MarketDataTool handler."""
    provider = _get_provider()
    try:
        if action == "get_quote":
            if not symbol:
                return {"error": "INVALID_ARGUMENT", "message": "symbol is required"}
            quote = await provider.get_realtime_quote(symbol)
            if quote is None:
                return {"status": "UNAVAILABLE", "symbol": symbol, "message": "No quote data"}
            return {
                "status": "OK",
                "symbol": symbol,
                "data": _to_serializable(quote),
                "source": getattr(quote, "data_source", "unknown"),
                "timestamp": getattr(quote, "timestamp", ""),
            }
        elif action == "get_kline":
            if not symbol:
                return {"error": "INVALID_ARGUMENT", "message": "symbol is required"}
            klines = await provider.get_kline(symbol, timeframe=timeframe, limit=limit)
            if not klines:
                return {"status": "UNAVAILABLE", "symbol": symbol, "message": "No kline data"}
            return {
                "status": "OK",
                "symbol": symbol,
                "count": len(klines),
                "data": [_to_serializable(k) for k in klines[-10:]],
                "source": "provider",
            }
        elif action == "get_market_snapshot":
            overview = await provider.get_market_overview()
            return {"status": "OK", "data": _to_serializable(overview)}
        else:
            return {"error": "INVALID_ARGUMENT", "message": f"Unknown action: {action}"}
    except Exception as e:
        logger.error("MarketDataTool error", action=action, symbol=symbol, error=str(e))
        return {"status": "ERROR", "message": str(e)}


MARKET_DATA_TOOL = Tool(
    name="get_market_data",
    description="获取A股市场数据。支持: get_quote(实时行情), get_kline(K线), get_market_snapshot(市场概览)",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["get_quote", "get_kline", "get_market_snapshot"]},
            "symbol": {"type": "string", "description": "股票代码"},
            "timeframe": {"type": "string", "enum": ["1d", "1w", "1m"], "default": "1d"},
            "limit": {"type": "integer", "default": 120},
        },
        "required": ["action"],
    },
    permission=ToolPermission.READ_ONLY,
    handler=_market_data_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
# Tool 2: TechnicalAnalysisTool
# ══════════════════════════════════════════════════════════════════════════════

async def _technical_analysis_handler(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 120,
) -> dict:
    """TechnicalAnalysisTool handler."""
    if not symbol:
        return {"error": "INVALID_ARGUMENT", "message": "symbol is required"}
    provider = _get_provider()
    from app.services.technical_analysis import TechnicalAnalysisService
    ta = TechnicalAnalysisService()
    try:
        klines = await provider.get_kline(symbol, timeframe=timeframe, limit=limit)
        if not klines:
            return {"status": "UNAVAILABLE", "symbol": symbol, "message": "No kline data for technical analysis"}
        indicators = ta.compute(klines)
        return {"status": "OK", "symbol": symbol, "data": _to_serializable(indicators), "kline_count": len(klines)}
    except Exception as e:
        logger.error("TechnicalAnalysisTool error", symbol=symbol, error=str(e))
        return {"status": "ERROR", "message": str(e)}


TECHNICAL_ANALYSIS_TOOL = Tool(
    name="analyze_technical",
    description="技术分析工具。计算MA/MACD/RSI/KDJ/BOLL/ATR等技术指标",
    parameters={
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "timeframe": {"type": "string", "enum": ["1d", "1w", "1m"], "default": "1d"},
            "limit": {"type": "integer", "default": 120},
        },
        "required": ["symbol"],
    },
    permission=ToolPermission.READ_ONLY,
    handler=_technical_analysis_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
# Tool 3: StockScreeningTool
# ══════════════════════════════════════════════════════════════════════════════

async def _stock_screening_handler(
    criteria: str = "trend_strong",
    top_n: int = 10,
) -> dict:
    """StockScreeningTool handler."""
    provider = _get_provider()
    from app.services.screening_engine import ScreeningEngine, ScreeningRule, FactorDirection
    engine = ScreeningEngine()
    try:
        stock_list = await provider.get_stock_list()
        if not stock_list:
            return {"status": "UNAVAILABLE", "message": "No stock list available"}
        candidates = []
        for stock in stock_list[:30]:
            sym = stock["symbol"]
            try:
                quote = await provider.get_realtime_quote(sym)
                klines = await provider.get_kline(sym, limit=60)
                candidates.append({"symbol": sym, "name": stock.get("name", ""), "quote": quote, "klines": klines})
            except Exception:
                continue
        if "trend" in criteria or "趋势" in criteria:
            rules = [
                ScreeningRule(name="ma_trend_up", factor="ma_trend", min_value=1.0, weight=3.0),
                ScreeningRule(name="positive_momentum", factor="momentum_5d", min_value=0.0, weight=2.0),
                ScreeningRule(name="volume_active", factor="volume_ratio", min_value=1.0, weight=1.0),
            ]
        elif "oversold" in criteria or "超卖" in criteria:
            rules = [ScreeningRule(name="rsi_oversold", factor="rsi", max_value=35.0, direction=FactorDirection.LOWER, weight=3.0)]
        elif "volume" in criteria or "放量" in criteria:
            rules = [
                ScreeningRule(name="high_volume_ratio", factor="volume_ratio", min_value=2.0, weight=3.0),
                ScreeningRule(name="positive_change", factor="change_pct", min_value=0.0, weight=1.0),
            ]
        else:
            rules = [
                ScreeningRule(name="reasonable_rsi", factor="rsi", min_value=30.0, max_value=70.0, weight=1.0),
                ScreeningRule(name="positive_momentum", factor="momentum_5d", min_value=-5.0, weight=1.0),
            ]
        result = engine.screen(candidates, rules, top_n=top_n)
        return {
            "status": "OK", "criteria": criteria,
            "total_screened": result.total_screened, "total_passed": result.total_passed,
            "candidates": [{"symbol": c.symbol, "name": c.name, "score": round(c.score, 2), "factors": c.factors} for c in result.candidates],
        }
    except Exception as e:
        logger.error("StockScreeningTool error", error=str(e))
        return {"status": "ERROR", "message": str(e)}


STOCK_SCREENING_TOOL = Tool(
    name="screen_stocks",
    description="股票筛选工具。根据条件筛选A股候选股票",
    parameters={
        "type": "object",
        "properties": {
            "criteria": {"type": "string", "default": "trend_strong"},
            "top_n": {"type": "integer", "default": 10},
        },
        "required": [],
    },
    permission=ToolPermission.READ_ONLY,
    handler=_stock_screening_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
# Tool 4: RiskTool
# ══════════════════════════════════════════════════════════════════════════════

async def _risk_handler(symbol: str) -> dict:
    """RiskTool handler."""
    if not symbol:
        return {"error": "INVALID_ARGUMENT", "message": "symbol is required"}
    provider = _get_provider()
    from app.risk.engine import RiskEngine
    risk_engine = RiskEngine()
    try:
        quote = await provider.get_realtime_quote(symbol)
        if quote is None:
            return {"status": "UNAVAILABLE", "symbol": symbol, "message": "Cannot assess risk without quote data"}
        risk_result = await risk_engine.check_order(
            symbol=symbol, side="buy", price=quote.price, quantity=100,
            order_amount=quote.price * 100, account_cash=1_000_000.0,
            total_asset=1_000_000.0, current_positions={},
            pre_close=quote.pre_close if quote.pre_close > 0 else None,
            data_age_seconds=0.0, is_data_available=True,
        )
        checks = [{"name": c.get("check", ""), "passed": c.get("passed", False)} for c in risk_result.checks]
        failed_count = sum(1 for c in checks if not c["passed"])
        blocked = not risk_result.passed
        risk_level = "EXTREME" if blocked else "HIGH" if failed_count >= 3 else "MEDIUM" if failed_count >= 1 else "LOW"
        return {
            "status": "OK", "symbol": symbol, "risk_level": risk_level,
            "risk_score": round(failed_count / max(len(checks), 1) * 100, 1),
            "blocked": blocked, "passed": risk_result.passed, "checks": checks,
            "rejection_reasons": risk_result.rejection_reasons,
            "warnings": [c["name"] for c in checks if not c["passed"]],
        }
    except Exception as e:
        logger.error("RiskTool error", symbol=symbol, error=str(e))
        return {"status": "ERROR", "message": str(e)}


RISK_TOOL = Tool(
    name="get_stock_risk",
    description="风险评估工具。对股票进行18项风控检查",
    parameters={"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
    permission=ToolPermission.READ_ONLY,
    handler=_risk_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
# Tool 5: PortfolioTool
# ══════════════════════════════════════════════════════════════════════════════

async def _portfolio_handler(action: str = "get_snapshot") -> dict:
    """PortfolioTool handler."""
    from app.portfolio.engine import PortfolioEngine
    engine = PortfolioEngine()
    try:
        if action == "get_snapshot":
            snapshot = engine.compute_snapshot(cash=1_000_000.0, positions=[], initial_capital=1_000_000.0)
            return {"status": "OK", "data": _to_serializable(snapshot), "mode": "paper_trading"}
        else:
            return {"error": "INVALID_ARGUMENT", "message": f"Unknown action: {action}"}
    except Exception as e:
        logger.error("PortfolioTool error", error=str(e))
        return {"status": "ERROR", "message": str(e)}


PORTFOLIO_TOOL = Tool(
    name="get_portfolio",
    description="组合管理工具。查看当前模拟交易组合状态",
    parameters={"type": "object", "properties": {"action": {"type": "string", "enum": ["get_snapshot"], "default": "get_snapshot"}}, "required": []},
    permission=ToolPermission.READ_ONLY,
    handler=_portfolio_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
# Tool 6: FinancialDataTool
# ══════════════════════════════════════════════════════════════════════════════

async def _financial_data_handler(symbol: str) -> dict:
    """FinancialDataTool handler. Returns financial snapshot from available data."""
    if not symbol:
        return {"error": "INVALID_ARGUMENT", "message": "symbol is required"}
    provider = _get_provider()
    try:
        # Try to get financial data from provider
        if hasattr(provider, 'get_financial_data'):
            fin = await provider.get_financial_data(symbol)
            if fin:
                return {
                    "status": "OK",
                    "symbol": symbol,
                    "data": _to_serializable(fin),
                    "source": getattr(fin, "data_source", "provider"),
                }
        # Try quote for basic info
        quote = await provider.get_realtime_quote(symbol)
        if quote:
            return {
                "status": "PARTIAL",
                "symbol": symbol,
                "data": {
                    "symbol": symbol,
                    "name": getattr(quote, "name", ""),
                    "price": getattr(quote, "price", 0),
                    "report_period": "unknown",
                    "published_at": "",
                    "source": getattr(quote, "data_source", "unknown"),
                    "data_quality": "PARTIAL",
                    "note": "Full financial data not available from current provider",
                },
                "source": getattr(quote, "data_source", "unknown"),
            }
        return {"status": "UNAVAILABLE", "symbol": symbol, "message": "Financial data not available"}
    except Exception as e:
        logger.error("FinancialDataTool error", symbol=symbol, error=str(e))
        return {"status": "ERROR", "message": str(e)}


FINANCIAL_DATA_TOOL = Tool(
    name="get_financial_data",
    description="财务数据工具。获取股票的财务指标: revenue, net_profit, ROE, PE, PB等",
    parameters={"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
    permission=ToolPermission.READ_ONLY,
    handler=_financial_data_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
# Tool 7: NewsSearchTool
# ══════════════════════════════════════════════════════════════════════════════

async def _news_search_handler(
    query: str = "",
    symbols: str = "",
    limit: int = 5,
) -> dict:
    """NewsSearchTool handler. Returns news articles."""
    try:
        # News search not yet implemented in provider
        return {
            "status": "UNAVAILABLE",
            "message": "News search not yet available",
            "query": query,
            "symbols": symbols.split(",") if symbols else [],
        }
    except Exception as e:
        logger.error("NewsSearchTool error", error=str(e))
        return {"status": "ERROR", "message": str(e)}


NEWS_SEARCH_TOOL = Tool(
    name="search_news",
    description="新闻搜索工具。搜索股票相关新闻",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "symbols": {"type": "string", "description": "股票代码，逗号分隔"},
            "limit": {"type": "integer", "default": 5},
        },
        "required": [],
    },
    permission=ToolPermission.READ_ONLY,
    handler=_news_search_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
# Tool 8: AnnouncementTool
# ══════════════════════════════════════════════════════════════════════════════

async def _announcement_handler(
    symbol: str,
    start_date: str = "",
    end_date: str = "",
) -> dict:
    """AnnouncementTool handler. Returns company announcements."""
    if not symbol:
        return {"error": "INVALID_ARGUMENT", "message": "symbol is required"}
    try:
        # Announcement search not yet implemented in provider
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": "Announcement search not yet available",
        }
    except Exception as e:
        logger.error("AnnouncementTool error", error=str(e))
        return {"status": "ERROR", "message": str(e)}


ANNOUNCEMENT_TOOL = Tool(
    name="get_announcements",
    description="公告查询工具。获取上市公司公告: 年报/季报/业绩预告/重大合同/股东变化/回购等",
    parameters={
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "start_date": {"type": "string", "description": "开始日期 YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
        },
        "required": ["symbol"],
    },
    permission=ToolPermission.READ_ONLY,
    handler=_announcement_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
# Registration
# ══════════════════════════════════════════════════════════════════════════════

ALL_BUILTIN_TOOLS = [
    MARKET_DATA_TOOL,
    TECHNICAL_ANALYSIS_TOOL,
    STOCK_SCREENING_TOOL,
    RISK_TOOL,
    PORTFOLIO_TOOL,
    FINANCIAL_DATA_TOOL,
    NEWS_SEARCH_TOOL,
    ANNOUNCEMENT_TOOL,
]


def register_builtin_tools(provider=None) -> None:
    """Register all built-in tools with the global registry."""
    global _shared_provider
    if provider is not None:
        _shared_provider = provider
    registry = get_tool_registry()
    for tool in ALL_BUILTIN_TOOLS:
        registry.register(tool)
    logger.info("Built-in tools registered", count=len(ALL_BUILTIN_TOOLS))
