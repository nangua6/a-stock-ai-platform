"""Moving average crossover strategy."""
from __future__ import annotations
from typing import Dict, List
from app.strategies.base import Strategy, StrategySignal


def _sma(data: List[float], period: int) -> float:
    if len(data) < period:
        return 0.0
    return sum(data[-period:]) / period


class MACrossStrategy(Strategy):
    def __init__(self, fast: int = 5, slow: int = 20):
        self.fast = fast
        self.slow = slow

    @property
    def name(self) -> str:
        return f"MA{self.fast}x{self.slow}"

    @property
    def version(self) -> str:
        return "v1"

    def universe(self) -> List[str]:
        return []

    def factors(self, symbol: str, data: dict) -> Dict[str, float]:
        closes = data.get("closes", [])
        if len(closes) < self.slow + 1:
            return {}
        return {
            "ma_fast": _sma(closes, self.fast),
            "ma_slow": _sma(closes, self.slow),
            "prev_ma_fast": _sma(closes[:-1], self.fast),
            "prev_ma_slow": _sma(closes[:-1], self.slow),
        }

    def signal(self, symbol: str, data: dict) -> StrategySignal:
        f = self.factors(symbol, data)
        if not f:
            return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
        closes = data.get("closes", [])
        price = closes[-1] if closes else 0
        if f["prev_ma_fast"] <= f["prev_ma_slow"] and f["ma_fast"] > f["ma_slow"]:
            return StrategySignal(
                symbol=symbol, direction="BUY", strength=0.6,
                entry_price=price,
                stop_loss=round(price * 0.95, 2),
                take_profit=round(price * 1.08, 2),
                position_target=0.05,
                reasons=[f"MA{self.fast} crossed above MA{self.slow}"],
                strategy_name=self.name,
            )
        elif f["prev_ma_fast"] >= f["prev_ma_slow"] and f["ma_fast"] < f["ma_slow"]:
            return StrategySignal(
                symbol=symbol, direction="SELL", strength=0.6,
                entry_price=price,
                reasons=[f"MA{self.fast} crossed below MA{self.slow}"],
                strategy_name=self.name,
            )
        return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
