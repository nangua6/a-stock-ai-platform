"""
Bollinger Band mean reversion strategy.

Buy: price touches or dips below lower band (oversold mean reversion)
Sell: price touches or breaks above upper band (overbought mean reversion)

Factors:
- Bollinger Band position (%B)
- Band width (volatility)
- RSI confirmation
- Volume confirmation
"""
from __future__ import annotations
import math
from typing import Dict, List
from app.strategies.base import Strategy, StrategySignal


def _sma(values: List[float], period: int) -> float:
    if len(values) < period:
        return 0.0
    return sum(values[-period:]) / period


def _bollinger(closes: List[float], period: int = 20, num_std: float = 2.0):
    """Returns (upper, middle, lower, %B)."""
    if len(closes) < period:
        return 0.0, 0.0, 0.0, 0.5
    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = math.sqrt(variance)
    upper = middle + num_std * std
    lower = middle - num_std * std
    # %B: position within bands (0 = at lower, 1 = at upper)
    band_width = upper - lower
    pct_b = (closes[-1] - lower) / band_width if band_width > 0 else 0.5
    return upper, middle, lower, pct_b


def _rsi(closes: List[float], period: int = 14) -> float:
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


class BollingerStrategy(Strategy):
    """
    Bollinger Band mean reversion strategy.

    Buys when price drops to lower band (oversold) with RSI confirmation.
    Sells when price reaches upper band (overbought).
    """

    def __init__(self, period: int = 20, num_std: float = 2.0,
                 rsi_confirm_buy: float = 35.0, rsi_confirm_sell: float = 65.0):
        self.period = period
        self.num_std = num_std
        self.rsi_confirm_buy = rsi_confirm_buy
        self.rsi_confirm_sell = rsi_confirm_sell

    @property
    def name(self) -> str:
        return "Bollinger"

    @property
    def version(self) -> str:
        return "v1"

    def universe(self) -> List[str]:
        return []

    def factors(self, symbol: str, data: dict) -> Dict[str, float]:
        closes = data.get("closes", [])
        if len(closes) < self.period + 1:
            return {}
        upper, middle, lower, pct_b = _bollinger(closes, self.period, self.num_std)
        band_width = (upper - lower) / middle * 100 if middle > 0 else 0
        return {
            "boll_upper": upper,
            "boll_middle": middle,
            "boll_lower": lower,
            "pct_b": pct_b,
            "band_width": band_width,
            "rsi": _rsi(closes),
        }

    def signal(self, symbol: str, data: dict) -> StrategySignal:
        f = self.factors(symbol, data)
        if not f:
            return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)

        closes = data.get("closes", [])
        price = closes[-1] if closes else 0
        pct_b = f["pct_b"]
        rsi = f["rsi"]
        band_width = f["band_width"]

        # Buy: price at or below lower band + RSI oversold confirmation
        if pct_b <= 0.05 and rsi < self.rsi_confirm_buy:
            strength = min((0.05 - pct_b) * 5 + (self.rsi_confirm_buy - rsi) / 50, 1.0)
            return StrategySignal(
                symbol=symbol, direction="BUY",
                strength=max(strength, 0.3),
                entry_price=price,
                stop_loss=round(f["boll_lower"] * 0.97, 2),
                take_profit=round(f["boll_middle"], 2),
                position_target=0.05,
                reasons=[
                    f"Price at lower Bollinger band (%B={pct_b:.2f})",
                    f"RSI={rsi:.1f} confirms oversold",
                    f"Band width={band_width:.1f}% (volatility context)",
                ],
                strategy_name=self.name,
            )

        # Buy: price slightly above lower band with strong RSI oversold
        if pct_b <= 0.20 and rsi < 25:
            return StrategySignal(
                symbol=symbol, direction="BUY",
                strength=0.4,
                entry_price=price,
                stop_loss=round(f["boll_lower"] * 0.97, 2),
                take_profit=round(f["boll_middle"], 2),
                position_target=0.03,
                reasons=[
                    f"Near lower band (%B={pct_b:.2f})",
                    f"RSI={rsi:.1f} deeply oversold",
                ],
                strategy_name=self.name,
            )

        # Sell: price at or above upper band + RSI overbought
        if pct_b >= 0.95 and rsi > self.rsi_confirm_sell:
            strength = min((pct_b - 0.95) * 5 + (rsi - self.rsi_confirm_sell) / 50, 1.0)
            return StrategySignal(
                symbol=symbol, direction="SELL",
                strength=max(strength, 0.3),
                entry_price=price,
                reasons=[
                    f"Price at upper Bollinger band (%B={pct_b:.2f})",
                    f"RSI={rsi:.1f} confirms overbought",
                ],
                strategy_name=self.name,
            )

        # Sell: price above upper band
        if pct_b >= 1.0:
            return StrategySignal(
                symbol=symbol, direction="SELL",
                strength=0.5,
                entry_price=price,
                reasons=[f"Price above upper Bollinger band (%B={pct_b:.2f})"],
                strategy_name=self.name,
            )

        return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
