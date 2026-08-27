"""
Built-in tools for the InvestmentResearchAgent.

Each tool wraps an existing service – never re-implements business logic.
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


# ══════════════════════════════════════════════════════════════════════════════
# Tool 1: MarketDataTool
# ══════════════════════════════════════════════════════════════════════════════

async def _market_data_handler(
    action: str,
    symbol: str = "",
    timeframe: str = "1d",
    limit: int = 120,
) -> dict:
    """
    MarketDataTool handler.

    Actions: get_quote, get_kline, get_market_snapshot
    """
    from app.market.provider_manager import ProviderManager
    from app.market.mock_provider import MockMarketDataProvider
    from app.market.cache import MarketDataCache

    cache = MarketDataCache()
    provider = ProviderManager(providers=[MockMarketDataProvider()], cache=cache)

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
                "data": [_to_serializable(k) for k in klines[-10:]],  # Last 10 for context
                "source": "provider",
            }

        elif action == "get_market_snapshot":
            overview = await provider.get_market_overview()
            return {
                "status": "OK",
                "data": _to_serializable(overview),
            }

        else:
            return {"error": "INVALID_ARGUMENT", "message": f"Unknown action: {action}"}

    except Exception as e:
        logger.error("MarketDataTool error", action=action, symbol=symbol, error=str(e))
        return {"status": "ERROR", "message": str(e)}


MARKET_DATA_TOOL = Tool(
    name="get_market_data",
    description=(
        "获取A股市场数据。支持三种操作：\n"
        "- get_quote: 获取单只股票实时行情（价格、涨跌幅、成交量等）\n"
        "- get_kline: 获取K线数据（日线、周线、月线）\n"
        "- get_market_snapshot: 获取市场概览（指数、涨跌家数等）"
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get_quote", "get_kline", "get_market_snapshot"],
                "description": "操作类型",
            },
            "symbol": {
                "type": "string",
                "description": "股票代码，如 600519.SH。get_market_snapshot 时不需要。",
            },
            "timeframe": {
                "type": "string",
                "enum": ["1d", "1w", "1m"],
                "description": "K线周期，默认 1d（日线）",
                "default": "1d",
            },
            "limit": {
                "type": "integer",
                "description": "K线数量，默认 120",
                "default": 120,
            },
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
    """TechnicalAnalysisTool handler. Computes indicators from kline data."""
    from app.market.provider_manager import ProviderManager
    from app.market.mock_provider import MockMarketDataProvider
    from app.market.cache import MarketDataCache
    from app.services.technical_analysis import TechnicalAnalysisService

    if not symbol:
        return {"error": "INVALID_ARGUMENT", "message": "symbol is required"}

    cache = MarketDataCache()
    provider = ProviderManager(providers=[MockMarketDataProvider()], cache=cache)
    ta = TechnicalAnalysisService()

    try:
        klines = await provider.get_kline(symbol, timeframe=timeframe, limit=limit)
        if not klines:
            return {"status": "UNAVAILABLE", "symbol": symbol, "message": "No kline data for technical analysis"}

        indicators = ta.compute(klines)
        return {
            "status": "OK",
            "symbol": symbol,
            "data": _to_serializable(indicators),
            "kline_count": len(klines),
        }
    except Exception as e:
        logger.error("TechnicalAnalysisTool error", symbol=symbol, error=str(e))
        return {"status": "ERROR", "message": str(e)}


TECHNICAL_ANALYSIS_TOOL = Tool(
    name="analyze_technical",
    description=(
        "技术分析工具。计算股票的技术指标：\n"
        "MA5/10/20/60, MACD, RSI, KDJ, BOLL, ATR, 成交量分析\n"
        "输入股票代码，返回完整技术指标数据。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "股票代码，如 600519.SH",
            },
            "timeframe": {
                "type": "string",
                "enum": ["1d", "1w", "1m"],
                "description": "分析周期，默认 1d",
                "default": "1d",
            },
            "limit": {
                "type": "integer",
                "description": "K线数量，默认 120",
                "default": 120,
            },
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
    market: Optional[str] = None,
    top_n: int = 10,
) -> dict:
    """StockScreeningTool handler. Wraps ScreeningEngine."""
    from app.market.provider_manager import ProviderManager
    from app.market.mock_provider import MockMarketDataProvider
    from app.market.cache import MarketDataCache
    from app.services.screening_engine import ScreeningEngine, ScreeningRule, FactorDirection

    cache = MarketDataCache()
    provider = ProviderManager(providers=[MockMarketDataProvider()], cache=cache)
    engine = ScreeningEngine()

    try:
        stock_list = await provider.get_stock_list()
        if not stock_list:
            return {"status": "UNAVAILABLE", "message": "No stock list available"}

        candidates = []
        for stock in stock_list[:30]:  # Limit to avoid timeout
            sym = stock["symbol"]
            try:
                quote = await provider.get_realtime_quote(sym)
                klines = await provider.get_kline(sym, limit=60)
                candidates.append({
                    "symbol": sym,
                    "name": stock.get("name", ""),
                    "quote": quote,
                    "klines": klines,
                })
            except Exception:
                continue

        # Map criteria string to rules
        if "trend" in criteria or "趋势" in criteria:
            rules = [
                ScreeningRule(name="ma_trend_up", factor="ma_trend", min_value=1.0, weight=3.0),
                ScreeningRule(name="positive_momentum", factor="momentum_5d", min_value=0.0, weight=2.0),
                ScreeningRule(name="volume_active", factor="volume_ratio", min_value=1.0, weight=1.0),
            ]
        elif "oversold" in criteria or "超卖" in criteria:
            rules = [
                ScreeningRule(name="rsi_oversold", factor="rsi", max_value=35.0, direction=FactorDirection.LOWER, weight=3.0),
            ]
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
            "status": "OK",
            "criteria": criteria,
            "total_screened": result.total_screened,
            "total_passed": result.total_passed,
            "candidates": [
                {
                    "symbol": c.symbol,
                    "name": c.name,
                    "score": round(c.score, 2),
                    "factors": c.factors,
                }
                for c in result.candidates
            ],
        }
    except Exception as e:
        logger.error("StockScreeningTool error", error=str(e))
        return {"status": "ERROR", "message": str(e)}


STOCK_SCREENING_TOOL = Tool(
    name="screen_stocks",
    description=(
        "股票筛选工具。根据条件筛选A股候选股票。\n"
        "支持筛选条件：\n"
        "- trend_strong: 趋势强势（均线多头、动量正、放量）\n"
        "- oversold: 超卖反弹（RSI低位）\n"
        "- volume_surge: 放量上涨\n"
        "返回按评分排序的候选股票列表。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "criteria": {
                "type": "string",
                "description": "筛选条件",
                "default": "trend_strong",
            },
            "top_n": {
                "type": "integer",
                "description": "返回数量，默认 10",
                "default": 10,
            },
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
    """RiskTool handler. Wraps RiskEngine for stock-level risk assessment."""
    from app.risk.engine import RiskEngine
    from app.market.provider_manager import ProviderManager
    from app.market.mock_provider import MockMarketDataProvider
    from app.market.cache import MarketDataCache

    if not symbol:
        return {"error": "INVALID_ARGUMENT", "message": "symbol is required"}

    cache = MarketDataCache()
    provider = ProviderManager(providers=[MockMarketDataProvider()], cache=cache)
    risk_engine = RiskEngine()

    try:
        quote = await provider.get_realtime_quote(symbol)
        if quote is None:
            return {
                "status": "UNAVAILABLE",
                "symbol": symbol,
                "message": "Cannot assess risk without quote data",
            }

        # Run risk checks using the engine (async, correct signature)
        risk_result = await risk_engine.check_order(
            symbol=symbol,
            side="buy",
            price=quote.price,
            quantity=100,
            order_amount=quote.price * 100,
            account_cash=1_000_000.0,
            total_asset=1_000_000.0,
            current_positions={},
            pre_close=quote.pre_close if quote.pre_close > 0 else None,
            data_age_seconds=0.0,
            is_data_available=True,
        )

        checks = []
        for check in risk_result.checks:
            checks.append({
                "name": check.get("check", ""),
                "passed": check.get("passed", False),
                "message": check.get("message", ""),
            })

        failed_count = sum(1 for c in checks if not c["passed"])
        blocked = not risk_result.passed

        if blocked:
            risk_level = "EXTREME"
        elif failed_count >= 3:
            risk_level = "HIGH"
        elif failed_count >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "status": "OK",
            "symbol": symbol,
            "risk_level": risk_level,
            "risk_score": round(failed_count / max(len(checks), 1) * 100, 1),
            "blocked": blocked,
            "passed": risk_result.passed,
            "checks": checks,
            "rejection_reasons": risk_result.rejection_reasons,
            "warnings": [c["name"] for c in checks if not c["passed"]],
        }
    except Exception as e:
        logger.error("RiskTool error", symbol=symbol, error=str(e))
        return {"status": "ERROR", "message": str(e)}


RISK_TOOL = Tool(
    name="get_stock_risk",
    description=(
        "风险评估工具。对股票进行18项风控检查：\n"
        "包括价格验证、涨跌停保护、ST检查、停牌检查、\n"
        "单笔金额、仓位比例、行业集中度等。\n"
        "返回风险等级（LOW/MEDIUM/HIGH/EXTREME）和详细检查结果。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "股票代码，如 600519.SH",
            },
        },
        "required": ["symbol"],
    },
    permission=ToolPermission.READ_ONLY,
    handler=_risk_handler,
)


# ══════════════════════════════════════════════════════════════════════════════
# Tool 5: PortfolioTool
# ══════════════════════════════════════════════════════════════════════════════

async def _portfolio_handler(action: str = "get_snapshot") -> dict:
    """PortfolioTool handler. Returns portfolio state."""
    from app.portfolio.engine import PortfolioEngine

    engine = PortfolioEngine()

    try:
        if action == "get_snapshot":
            # Default demo portfolio for paper trading
            snapshot = engine.compute_snapshot(
                cash=1_000_000.0,
                positions=[],
                initial_capital=1_000_000.0,
            )
            return {
                "status": "OK",
                "data": _to_serializable(snapshot),
                "mode": "paper_trading",
            }
        else:
            return {"error": "INVALID_ARGUMENT", "message": f"Unknown action: {action}"}
    except Exception as e:
        logger.error("PortfolioTool error", action=action, error=str(e))
        return {"status": "ERROR", "message": str(e)}


PORTFOLIO_TOOL = Tool(
    name="get_portfolio",
    description=(
        "组合管理工具。查看当前模拟交易组合状态：\n"
        "总资产、现金、持仓、市值、盈亏、最大回撤等。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get_snapshot"],
                "description": "操作类型",
                "default": "get_snapshot",
            },
        },
        "required": [],
    },
    permission=ToolPermission.READ_ONLY,
    handler=_portfolio_handler,
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
]


def register_builtin_tools() -> None:
    """Register all built-in tools with the global registry."""
    registry = get_tool_registry()
    for tool in ALL_BUILTIN_TOOLS:
        registry.register(tool)
    logger.info("Built-in tools registered", count=len(ALL_BUILTIN_TOOLS))
