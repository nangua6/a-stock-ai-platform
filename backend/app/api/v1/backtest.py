"""Backtesting endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from app.backtest.engine import BacktestConfig, BacktestEngine
from app.market.mock_provider import MockMarketDataProvider
from app.strategies.builtin import MACDStrategy, MACrossStrategy, RSIStrategy, MomentumStrategy, BollingerStrategy, ValueStrategy

router = APIRouter()
_provider = MockMarketDataProvider()

STRATEGY_MAP = {
    "MACD": MACDStrategy,
    "MA5x20": lambda: MACrossStrategy(5, 20),
    "RSI": RSIStrategy,
    "Momentum": MomentumStrategy,
    "Bollinger": BollingerStrategy,
    "Value": ValueStrategy,
}

STRATEGY_INFO = {
    "MACD": {"name": "MACD", "type": "趋势跟踪", "desc": "MACD 金叉/死叉策略", "period": "日线"},
    "MA5x20": {"name": "MA5×20", "type": "均线交叉", "desc": "5日/20日均线交叉策略", "period": "日线"},
    "RSI": {"name": "RSI", "type": "超买超卖", "desc": "RSI 超买超卖策略", "period": "日线"},
    "Momentum": {"name": "Momentum", "type": "动量因子", "desc": "动量因子策略", "period": "日线"},
    "Bollinger": {"name": "Bollinger", "type": "波动突破", "desc": "布林带突破策略", "period": "日线"},
    "Value": {"name": "Value", "type": "价值因子", "desc": "价值因子策略", "period": "日线"},
}


class BacktestRequest(BaseModel):
    strategy: str = "MACD"
    symbols: List[str] = ["600519.SH"]
    start_date: str = "2025-01-01"
    end_date: str = "2026-08-25"
    initial_capital: float = 1_000_000.0
    commission_rate: float = 0.0003
    slippage_rate: float = 0.001


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """Run a backtest with the specified strategy and parameters."""
    strategy_cls = STRATEGY_MAP.get(request.strategy)
    if not strategy_cls:
        return {"success": False, "message": f"Unknown strategy: {request.strategy}. Available: {list(STRATEGY_MAP.keys())}"}

    strategy = strategy_cls() if callable(strategy_cls) else strategy_cls
    config = BacktestConfig(
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        commission_rate=request.commission_rate,
        slippage_rate=request.slippage_rate,
    )
    engine = BacktestEngine(config)
    result = await engine.run(strategy, request.symbols, _provider)

    return {"success": True, "data": {
        "strategy_name": result.strategy_name,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "final_capital": result.final_capital,
        "total_return": result.total_return,
        "annualized_return": result.annualized_return,
        "sharpe_ratio": result.sharpe_ratio,
        "max_drawdown": result.max_drawdown,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "total_trades": result.total_trades,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
        "avg_win": result.avg_win,
        "avg_loss": result.avg_loss,
        "trades": [t.__dict__ for t in result.trades],
        "equity_curve": result.equity_curve,
        "data_source": "mock",
    }}


@router.get("/strategies")
async def list_strategies():
    """List available backtest strategies with metadata."""
    strategies = []
    for key, info in STRATEGY_INFO.items():
        strategies.append({
            "key": key,
            "name": info["name"],
            "type": info["type"],
            "desc": info["desc"],
            "period": info["period"],
        })
    return {"success": True, "data": strategies}
