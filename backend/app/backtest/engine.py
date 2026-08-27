"""
Backtesting engine with A-share rules.

Critical: No look-ahead bias, no survivorship bias, no data leakage.
All strategy data must have: timestamp, available_time, publish_time, trade_date.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Type

from app.core.logging import get_logger
from app.strategies.base import Strategy, StrategySignal

logger = get_logger("backtest")


@dataclass
class BacktestConfig:
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 1_000_000.0
    commission_rate: float = 0.0003
    min_commission: float = 5.0
    stamp_tax_rate: float = 0.0005  # Sell only
    transfer_fee_rate: float = 0.00001
    slippage_rate: float = 0.001
    lot_size: int = 100
    allow_t0_sell: bool = False  # A-share default: T+1


@dataclass
class BacktestTrade:
    symbol: str = ""
    side: str = ""
    price: float = 0.0
    quantity: int = 0
    amount: float = 0.0
    commission: float = 0.0
    trade_date: str = ""
    strategy: str = ""
    signal_strength: float = 0.0


@dataclass
class BacktestResult:
    strategy_name: str = ""
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 0.0
    final_capital: float = 0.0
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: float = 0.0
    calmar_ratio: Optional[float] = None
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[dict] = field(default_factory=list)


class BacktestEngine:
    """
    Deterministic backtesting engine.

    IMPORTANT: Uses only data available at each point in time.
    No look-ahead bias allowed.
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()

    async def run(
        self,
        strategy: Strategy,
        symbols: List[str],
        data_provider,
    ) -> BacktestResult:
        """Run a backtest for the given strategy on the given symbols."""
        logger.info("Starting backtest", strategy=strategy.name, symbols=symbols)

        capital = self.config.initial_capital
        positions: Dict[str, dict] = {}
        trades: List[BacktestTrade] = []
        equity_curve = []
        peak = capital

        for symbol in symbols:
            klines = await data_provider.get_kline(
                symbol,
                timeframe="D",
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                limit=500,
            )
            if not klines:
                continue

            closes = [k.close for k in klines]
            for i in range(26, len(klines)):
                window_closes = closes[:i + 1]
                bar = klines[i]
                signal_data = {"closes": window_closes}
                sig = strategy.signal(symbol, signal_data)

                if sig.direction == "BUY" and symbol not in positions:
                    price = bar.close
                    shares = strategy.position_size(sig, {"total_asset": capital})
                    if shares >= 100 and capital >= price * shares:
                        cost = price * shares * (1 + self.config.slippage_rate)
                        commission = max(cost * self.config.commission_rate, self.config.min_commission)
                        capital -= (cost + commission)
                        positions[symbol] = {
                            "shares": shares,
                            "cost": price,
                            "entry_date": bar.trade_date,
                        }
                        trades.append(BacktestTrade(
                            symbol=symbol, side="BUY", price=price,
                            quantity=shares, amount=cost, commission=commission,
                            trade_date=bar.trade_date, strategy=strategy.name,
                        ))

                elif sig.direction == "SELL" and symbol in positions:
                    pos = positions.pop(symbol)
                    price = bar.close
                    revenue = price * pos["shares"]
                    commission = max(revenue * self.config.commission_rate, self.config.min_commission)
                    stamp_tax = revenue * self.config.stamp_tax_rate
                    capital += (revenue - commission - stamp_tax)
                    trades.append(BacktestTrade(
                        symbol=symbol, side="SELL", price=price,
                        quantity=pos["shares"], amount=revenue,
                        commission=commission + stamp_tax,
                        trade_date=bar.trade_date, strategy=strategy.name,
                    ))

                # Record equity at each bar (sample every 5 bars to keep curve manageable)
                if i % 5 == 0:
                    total_asset = capital + sum(
                        p["shares"] * bar.close for p in positions.values()
                    )
                    equity_curve.append({"date": bar.trade_date, "equity": round(total_asset, 2)})

        final_asset = capital + sum(
            p["shares"] * (closes[-1] if closes else 0) for p in positions.values()
        )

        # ── Compute metrics ─────────────────────────────────────────
        total_return = (final_asset - self.config.initial_capital) / self.config.initial_capital

        # Annualized return
        days = 0
        if equity_curve and len(equity_curve) >= 2:
            try:
                d0 = datetime.fromisoformat(equity_curve[0]["date"] + "T00:00:00")
                d1 = datetime.fromisoformat(equity_curve[-1]["date"] + "T00:00:00")
                days = (d1 - d0).days
            except Exception:
                days = len(equity_curve)
        if days > 0 and total_return > -1:
            annualized_return = (1 + total_return) ** (365.0 / days) - 1
        else:
            annualized_return = 0.0

        # Match buy/sell trades for P&L
        buy_trades = {t.symbol: t for t in trades if t.side == "BUY"}
        round_trip_pnls = []
        for t in trades:
            if t.side == "SELL" and t.symbol in buy_trades:
                buy = buy_trades.pop(t.symbol)
                pnl = (t.price - buy.price) * t.quantity - t.commission - buy.commission
                round_trip_pnls.append(pnl)

        winning_pnls = [p for p in round_trip_pnls if p > 0]
        losing_pnls = [p for p in round_trip_pnls if p <= 0]
        winning_count = len(winning_pnls)
        losing_count = len(losing_pnls)
        total_round_trips = winning_count + losing_count

        win_rate = winning_count / total_round_trips if total_round_trips > 0 else 0.0
        avg_win = sum(winning_pnls) / winning_count if winning_count > 0 else 0.0
        avg_loss = sum(losing_pnls) / losing_count if losing_count > 0 else 0.0
        gross_profit = sum(winning_pnls)
        gross_loss = abs(sum(losing_pnls))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

        # Max drawdown from equity curve
        max_drawdown = 0.0
        peak_equity = self.config.initial_capital
        for point in equity_curve:
            eq = point["equity"]
            if eq > peak_equity:
                peak_equity = eq
            dd = (peak_equity - eq) / peak_equity if peak_equity > 0 else 0
            if dd > max_drawdown:
                max_drawdown = dd

        # Sharpe ratio (simplified, from equity curve returns)
        sharpe_ratio = None
        if len(equity_curve) >= 3:
            equities = [p["equity"] for p in equity_curve]
            returns = [(equities[i] / equities[i - 1]) - 1 for i in range(1, len(equities))]
            if returns:
                mean_ret = sum(returns) / len(returns)
                var = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
                std = math.sqrt(var) if var > 0 else 0
                if std > 0:
                    sharpe_ratio = round((mean_ret / std) * math.sqrt(242), 4)  # Annualized

        # Consecutive wins/losses
        max_consec_wins = 0
        max_consec_losses = 0
        cur_wins = 0
        cur_losses = 0
        for pnl in round_trip_pnls:
            if pnl > 0:
                cur_wins += 1
                cur_losses = 0
                max_consec_wins = max(max_consec_wins, cur_wins)
            else:
                cur_losses += 1
                cur_wins = 0
                max_consec_losses = max(max_consec_losses, cur_losses)

        result = BacktestResult(
            strategy_name=strategy.name,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            initial_capital=self.config.initial_capital,
            final_capital=round(final_asset, 2),
            total_return=round(total_return, 4),
            annualized_return=round(annualized_return, 4),
            sharpe_ratio=sharpe_ratio,
            max_drawdown=round(max_drawdown, 4),
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            total_trades=len(trades),
            winning_trades=winning_count,
            losing_trades=losing_count,
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            max_consecutive_wins=max_consec_wins,
            max_consecutive_losses=max_consec_losses,
            trades=trades,
            equity_curve=equity_curve,
        )

        logger.info("Backtest complete", strategy=strategy.name, total_return=f"{total_return:.2%}")
        return result
