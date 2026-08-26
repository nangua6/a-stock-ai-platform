"""Portfolio management endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.broker.paper_broker import PaperBroker
from app.portfolio.engine import PortfolioEngine

router = APIRouter()
_broker = PaperBroker()
_portfolio = PortfolioEngine()


@router.get("/summary")
async def get_portfolio_summary():
    """Get portfolio summary with all metrics."""
    account = await _broker.get_account()
    positions = await _broker.get_positions()
    pos_dicts = [p.__dict__ for p in positions]
    snapshot = _portfolio.compute_snapshot(
        cash=account.cash,
        positions=pos_dicts,
        initial_capital=1_000_000.0,
    )
    return {"success": True, "data": {
        "total_asset": snapshot.total_asset,
        "cash": snapshot.cash,
        "market_value": snapshot.market_value,
        "unrealized_pnl": snapshot.unrealized_pnl,
        "unrealized_pnl_pct": snapshot.unrealized_pnl_pct,
        "max_drawdown": snapshot.max_drawdown,
        "win_rate": snapshot.win_rate,
        "profit_factor": snapshot.profit_factor,
        "total_trades": snapshot.total_trades,
        "positions": snapshot.positions,
        "industry_exposures": snapshot.industry_exposures,
        "top_positions": snapshot.top_positions,
    }}


@router.get("/risk")
async def get_portfolio_risk():
    """Get portfolio risk metrics."""
    account = await _broker.get_account()
    positions = await _broker.get_positions()
    pos_dicts = [p.__dict__ for p in positions]
    snapshot = _portfolio.compute_snapshot(
        cash=account.cash,
        positions=pos_dicts,
        initial_capital=1_000_000.0,
    )
    return {"success": True, "data": {
        "total_asset": snapshot.total_asset,
        "max_drawdown": snapshot.max_drawdown,
        "position_count": len(positions),
        "industry_exposures": snapshot.industry_exposures,
        "top_positions": snapshot.top_positions,
    }}
