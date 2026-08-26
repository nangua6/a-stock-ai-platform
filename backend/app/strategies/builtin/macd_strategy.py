"""MACD crossover strategy."""
from __future__ import annotations
from typing import Dict, List
from app.strategies.base import Strategy, StrategySignal


def _ema(data: List[float], period: int) -> List[float]:
    if not data:
        return []
    multiplier = 2 / (period + 1)
    ema_values = [data[0]]
    for i in range(1, len(data)):
        ema_values.append(data[i] * multiplier + ema_values[-1] * (1 - multiplier))
    return ema_values


def _macd(closes: List[float], fast: int = 12, slow: int = 26, signal_period: int = 9):
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = _ema(macd_line, signal_period)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, histogram


class MACDStrategy(Strategy):
    @property
    def name(self) -> str:
        return "MACD"

    @property
    def version(self) -> str:
        return "v1"

    def universe(self) -> List[str]:
        return []

    def factors(self, symbol: str, data: dict) -> Dict[str, float]:
        closes = data.get("closes", [])
        if len(closes) < 35:
            return {}
        macd_line, signal_line, histogram = _macd(closes)
        return {
            "macd": macd_line[-1],
            "signal": signal_line[-1],
            "histogram": histogram[-1],
            "prev_histogram": histogram[-2] if len(histogram) > 1 else 0,
        }

    def signal(self, symbol: str, data: dict) -> StrategySignal:
        factors = self.factors(symbol, data)
        if not factors:
            return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
        hist = factors["histogram"]
        prev_hist = factors["prev_histogram"]
        closes = data.get("closes", [])
        current_price = closes[-1] if closes else 0
        if prev_hist < 0 and hist > 0:
            return StrategySignal(
                symbol=symbol, direction="BUY",
                strength=min(abs(hist) / current_price * 100, 1.0) if current_price else 0.5,
                entry_price=current_price,
                stop_loss=round(current_price * 0.95, 2),
                take_profit=round(current_price * 1.10, 2),
                position_target=0.05,
                reasons=["MACD histogram crossed zero from below (bullish crossover)"],
                strategy_name=self.name,
            )
        elif prev_hist > 0 and hist < 0:
            return StrategySignal(
                symbol=symbol, direction="SELL",
                strength=min(abs(hist) / current_price * 100, 1.0) if current_price else 0.5,
                entry_price=current_price,
                reasons=["MACD histogram crossed zero from above (bearish crossover)"],
                strategy_name=self.name,
            )
        return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
