"""RSI overbought/oversold strategy."""
from __future__ import annotations
from typing import Dict, List
from app.strategies.base import Strategy, StrategySignal


class RSIStrategy(Strategy):
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    @property
    def name(self) -> str:
        return "RSI"

    @property
    def version(self) -> str:
        return "v1"

    def universe(self) -> List[str]:
        return []

    def factors(self, symbol: str, data: dict) -> Dict[str, float]:
        closes = data.get("closes", [])
        if len(closes) < self.period + 1:
            return {}
        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        return {"rsi": rsi}

    def signal(self, symbol: str, data: dict) -> StrategySignal:
        f = self.factors(symbol, data)
        if not f:
            return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
        rsi = f["rsi"]
        closes = data.get("closes", [])
        price = closes[-1] if closes else 0
        if rsi < self.oversold:
            return StrategySignal(
                symbol=symbol, direction="BUY", strength=0.7,
                entry_price=price,
                stop_loss=round(price * 0.93, 2),
                take_profit=round(price * 1.12, 2),
                position_target=0.05,
                reasons=[f"RSI={rsi:.1f} below oversold threshold {self.oversold}"],
                strategy_name=self.name,
            )
        elif rsi > self.overbought:
            return StrategySignal(
                symbol=symbol, direction="SELL", strength=0.7,
                entry_price=price,
                reasons=[f"RSI={rsi:.1f} above overbought threshold {self.overbought}"],
                strategy_name=self.name,
            )
        return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
