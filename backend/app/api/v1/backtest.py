"""Backtesting endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from app.backtest.engine import BacktestConfig, BacktestEngine
from app.market.mock_provider import MockMarketDataProvider
from app.strategies.builtin import MACDStrategy, MACrossStrategy, RSIStrategy

router = APIRouter()
_provider = MockMarketDataProvider()

STRATEGY_MAP = {
    "MACD": MACDStrategy,
    "MA5x20": lambda: MACrossStrategy(5, 20),
    "RSI": RSIStrategy,
}


class BacktestRequest(BaseModel):
    strategy: str = "MACD"
    symbols: List[str] = ["600519.SH"]
    start_date: str = "2025-01-01"
    end_date: str = "2026-08-25"
    initial_capital: float = 1_000_000.0


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
        "total_trades": result.total_trades,
        "trades": [t.__dict__ for t in result.trades],
        "equity_curve": result.equity_curve[-20:],
    }}


@router.get("/strategies")
async def list_strategies():
    """List available backtest strategies."""
    return {"success": True, "data": list(STRATEGY_MAP.keys())}
