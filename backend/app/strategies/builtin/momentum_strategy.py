"""
Price momentum strategy.

Buy: strong upward momentum (positive ROC + RSI rising but not overbought)
Sell: momentum reversal (negative ROC + RSI falling from overbought)

Factors:
- ROC (Rate of Change) over 5, 10, 20 days
- RSI (14-period)
- Volume momentum (volume MA ratio)
- Price relative to MA20 (trend filter)
"""
from __future__ import annotations
from typing import Dict, List
from app.strategies.base import Strategy, StrategySignal


def _roc(closes: List[float], period: int) -> float:
    """Rate of Change over `period` bars."""
    if len(closes) < period + 1 or closes[-period - 1] == 0:
        return 0.0
    return (closes[-1] / closes[-period - 1] - 1) * 100


def _rsi(closes: List[float], period: int = 14) -> float:
    """RSI calculation."""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _sma(values: List[float], period: int) -> float:
    if len(values) < period:
        return 0.0
    return sum(values[-period:]) / period


class MomentumStrategy(Strategy):
    """
    Momentum strategy: buys stocks with strong positive momentum
    that is not yet overbought. Sells when momentum reverses.
    """

    def __init__(self, roc_period: int = 10, rsi_period: int = 14,
                 rsi_buy_max: float = 70.0, rsi_sell_min: float = 65.0):
        self.roc_period = roc_period
        self.rsi_period = rsi_period
        self.rsi_buy_max = rsi_buy_max
        self.rsi_sell_min = rsi_sell_min

    @property
    def name(self) -> str:
        return "Momentum"

    @property
    def version(self) -> str:
        return "v1"

    def universe(self) -> List[str]:
        return []

    def factors(self, symbol: str, data: dict) -> Dict[str, float]:
        closes = data.get("closes", [])
        if len(closes) < max(self.roc_period + 1, self.rsi_period + 1, 21):
            return {}
        volumes = data.get("volumes", [])
        return {
            "roc_5": _roc(closes, 5),
            "roc_10": _roc(closes, self.roc_period),
            "roc_20": _roc(closes, 20),
            "rsi": _rsi(closes, self.rsi_period),
            "ma20": _sma(closes, 20),
            "price_vs_ma20": (closes[-1] / _sma(closes, 20) - 1) * 100 if _sma(closes, 20) > 0 else 0,
            "vol_ratio": (volumes[-1] / _sma(volumes, 5)) if volumes and len(volumes) >= 5 and _sma(volumes, 5) > 0 else 1.0,
        }

    def signal(self, symbol: str, data: dict) -> StrategySignal:
        f = self.factors(symbol, data)
        if not f:
            return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)

        closes = data.get("closes", [])
        price = closes[-1] if closes else 0
        roc = f["roc_10"]
        rsi = f["rsi"]
        above_ma = f["price_vs_ma20"] > 0

        # Buy: strong positive ROC + RSI not overbought + above MA20
        if roc > 3.0 and rsi < self.rsi_buy_max and above_ma:
            strength = min(roc / 10.0, 1.0)
            return StrategySignal(
                symbol=symbol, direction="BUY",
                strength=strength,
                entry_price=price,
                stop_loss=round(price * 0.95, 2),
                take_profit=round(price * 1.10, 2),
                position_target=0.05,
                reasons=[
                    f"ROC({self.roc_period}d)={roc:.1f}% (strong momentum)",
                    f"RSI={rsi:.1f} (not overbought)",
                    f"Price above MA20 ({f['price_vs_ma20']:+.1f}%)",
                ],
                strategy_name=self.name,
            )

        # Sell: negative ROC + RSI falling from high
        if roc < -2.0 and rsi > self.rsi_sell_min:
            return StrategySignal(
                symbol=symbol, direction="SELL",
                strength=min(abs(roc) / 10.0, 1.0),
                entry_price=price,
                reasons=[
                    f"ROC({self.roc_period}d)={roc:.1f}% (momentum reversal)",
                    f"RSI={rsi:.1f} (elevated, likely to fall)",
                ],
                strategy_name=self.name,
            )

        # Sell: ROC strongly negative
        if roc < -5.0:
            return StrategySignal(
                symbol=symbol, direction="SELL",
                strength=min(abs(roc) / 10.0, 1.0),
                entry_price=price,
                reasons=[f"ROC({self.roc_period}d)={roc:.1f}% (sharp decline)"],
                strategy_name=self.name,
            )

        return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
