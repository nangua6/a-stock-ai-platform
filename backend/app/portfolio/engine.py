"""
Portfolio Engine – tracks account state and computes portfolio metrics.

Metrics: total_asset, cash, positions, market_value, unrealized/realized PnL,
max_drawdown, Sharpe, win_rate, profit_factor, beta, industry exposure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger("portfolio")


@dataclass
class PortfolioSnapshot:
    total_asset: float = 0.0
    cash: float = 0.0
    market_value: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: Optional[float] = None
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    positions: List[dict] = field(default_factory=list)
    industry_exposures: Dict[str, float] = field(default_factory=dict)
    top_positions: List[dict] = field(default_factory=list)


class PortfolioEngine:
    """Manages and analyzes portfolio state."""

    def __init__(self):
        self._equity_history: List[float] = []
        self._trade_results: List[float] = []

    def compute_snapshot(
        self,
        cash: float,
        positions: List[dict],
        initial_capital: float,
    ) -> PortfolioSnapshot:
        """Compute current portfolio snapshot."""
        market_value = sum(p.get("market_value", 0) for p in positions)
        total_asset = cash + market_value
        unrealized_pnl = total_asset - initial_capital
        unrealized_pnl_pct = unrealized_pnl / initial_capital if initial_capital > 0 else 0

        # Max drawdown from equity history
        self._equity_history.append(total_asset)
        peak = max(self._equity_history)
        drawdown = (peak - total_asset) / peak if peak > 0 else 0

        # Win rate
        wins = [t for t in self._trade_results if t > 0]
        losses = [t for t in self._trade_results if t < 0]
        win_rate = len(wins) / len(self._trade_results) if self._trade_results else 0
        total_win = sum(wins) if wins else 0
        total_loss = abs(sum(losses)) if losses else 1
        profit_factor = total_win / total_loss if total_loss > 0 else 0

        # Industry exposure
        industry_exposures: Dict[str, float] = {}
        for p in positions:
            ind = p.get("industry", "其他")
            industry_exposures[ind] = industry_exposures.get(ind, 0) + p.get("market_value", 0)

        # Top positions by market value
        sorted_positions = sorted(positions, key=lambda x: x.get("market_value", 0), reverse=True)
        top = sorted_positions[:5]

        return PortfolioSnapshot(
            total_asset=total_asset,
            cash=cash,
            market_value=market_value,
            unrealized_pnl=round(unrealized_pnl, 2),
            unrealized_pnl_pct=round(unrealized_pnl_pct, 4),
            max_drawdown=round(drawdown, 4),
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            total_trades=len(self._trade_results),
            winning_trades=len(wins),
            losing_trades=len(losses),
            positions=positions,
            industry_exposures=industry_exposures,
            top_positions=top,
        )

    def record_trade(self, pnl: float):
        """Record a completed trade result for metrics."""
        self._trade_results.append(pnl)
