"""
PE/PB value investing strategy.

Buy: low PE + low PB relative to historical range + positive earnings
Sell: PE/PB stretched beyond fair value or earnings deterioration

Note: This strategy uses fundamental data (PE, PB, ROE) from the data dict.
If fundamental data is unavailable, it falls back to price-based value signals.

Factors:
- PE ratio (from fundamental data or data dict)
- PB ratio
- ROE
- Price vs 60-day MA (value proxy)
- Dividend yield (if available)
"""
from __future__ import annotations
from typing import Dict, List
from app.strategies.base import Strategy, StrategySignal


def _sma(values: List[float], period: int) -> float:
    if len(values) < period:
        return 0.0
    return sum(values[-period:]) / period


class ValueStrategy(Strategy):
    """
    Value investing strategy.

    Buys fundamentally cheap stocks (low PE, low PB, decent ROE).
    Sells when valuation becomes stretched.
    """

    # Value thresholds (A-share market context)
    PE_CHEAP = 15.0       # PE below this is considered cheap
    PE_FAIR = 25.0        # PE around this is fair value
    PE_EXPENSIVE = 40.0   # PE above this is expensive
    PB_CHEAP = 1.5        # PB below this is cheap
    PB_FAIR = 3.0         # PB fair value
    PB_EXPENSIVE = 5.0    # PB expensive
    ROE_MIN = 8.0         # Minimum ROE for value stock

    @property
    def name(self) -> str:
        return "Value"

    @property
    def version(self) -> str:
        return "v1"

    def universe(self) -> List[str]:
        return []

    def factors(self, symbol: str, data: dict) -> Dict[str, float]:
        factors = {}

        # Fundamental factors from data dict
        pe = data.get("pe_ratio", data.get("pe", 0))
        pb = data.get("pb_ratio", data.get("pb", 0))
        roe = data.get("roe", 0)
        market_cap = data.get("market_cap", 0)
        dividend_yield = data.get("dividend_yield", 0)

        if pe and pe > 0:
            factors["pe"] = float(pe)
        if pb and pb > 0:
            factors["pb"] = float(pb)
        if roe:
            factors["roe"] = float(roe)
        if market_cap and market_cap > 0:
            factors["market_cap"] = float(market_cap)
        if dividend_yield and dividend_yield > 0:
            factors["dividend_yield"] = float(dividend_yield)

        # Price-based value proxy
        closes = data.get("closes", [])
        if len(closes) >= 60:
            ma60 = _sma(closes, 60)
            if ma60 > 0:
                factors["price_vs_ma60"] = (closes[-1] / ma60 - 1) * 100

        # Composite value score (lower = cheaper)
        value_score = 0
        count = 0
        if "pe" in factors and factors["pe"] > 0:
            # Normalize PE: 0-100 where lower is better value
            pe_score = max(0, min(100, (1 - factors["pe"] / self.PE_EXPENSIVE) * 100))
            value_score += pe_score
            count += 1
        if "pb" in factors and factors["pb"] > 0:
            pb_score = max(0, min(100, (1 - factors["pb"] / self.PB_EXPENSIVE) * 100))
            value_score += pb_score
            count += 1
        if "roe" in factors:
            roe_score = min(100, factors["roe"] / 20 * 100)
            value_score += roe_score
            count += 1

        if count > 0:
            factors["value_score"] = value_score / count

        return factors

    def signal(self, symbol: str, data: dict) -> StrategySignal:
        f = self.factors(symbol, data)
        if not f:
            return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)

        closes = data.get("closes", [])
        price = closes[-1] if closes else 0
        pe = f.get("pe", 0)
        pb = f.get("pb", 0)
        roe = f.get("roe", 0)
        value_score = f.get("value_score", 50)

        reasons = []

        # Buy: cheap valuation
        is_cheap_pe = pe > 0 and pe < self.PE_CHEAP
        is_cheap_pb = pb > 0 and pb < self.PB_CHEAP
        has_decent_roe = roe >= self.ROE_MIN or roe == 0  # ROE=0 means unknown

        if is_cheap_pe and is_cheap_pb and has_decent_roe:
            strength = min((self.PE_CHEAP - pe) / self.PE_CHEAP * 0.5 +
                          (self.PB_CHEAP - pb) / self.PB_CHEAP * 0.5, 1.0)
            reasons = [
                f"PE={pe:.1f} below cheap threshold ({self.PE_CHEAP})",
                f"PB={pb:.1f} below cheap threshold ({self.PB_CHEAP})",
            ]
            if roe > 0:
                reasons.append(f"ROE={roe:.1f}%")
            return StrategySignal(
                symbol=symbol, direction="BUY",
                strength=max(strength, 0.3),
                entry_price=price,
                stop_loss=round(price * 0.90, 2),
                take_profit=round(price * 1.20, 2),
                position_target=0.05,
                reasons=reasons,
                strategy_name=self.name,
            )

        # Buy: moderately cheap with good ROE
        if pe > 0 and pe < self.PE_FAIR and pb > 0 and pb < self.PB_FAIR and roe >= self.ROE_MIN:
            strength = 0.4
            return StrategySignal(
                symbol=symbol, direction="BUY",
                strength=strength,
                entry_price=price,
                stop_loss=round(price * 0.92, 2),
                take_profit=round(price * 1.15, 2),
                position_target=0.03,
                reasons=[
                    f"PE={pe:.1f} (fair-cheap range)",
                    f"PB={pb:.1f} (fair-cheap range)",
                    f"ROE={roe:.1f}% (meets minimum)",
                ],
                strategy_name=self.name,
            )

        # Sell: expensive valuation
        if pe > self.PE_EXPENSIVE or pb > self.PB_EXPENSIVE:
            reasons = []
            if pe > self.PE_EXPENSIVE:
                reasons.append(f"PE={pe:.1f} above expensive threshold ({self.PE_EXPENSIVE})")
            if pb > self.PB_EXPENSIVE:
                reasons.append(f"PB={pb:.1f} above expensive threshold ({self.PB_EXPENSIVE})")
            return StrategySignal(
                symbol=symbol, direction="SELL",
                strength=0.6,
                entry_price=price,
                reasons=reasons,
                strategy_name=self.name,
            )

        # Sell: ROE deterioration with moderate valuation
        if roe > 0 and roe < 3.0 and pe > self.PE_FAIR:
            return StrategySignal(
                symbol=symbol, direction="SELL",
                strength=0.4,
                entry_price=price,
                reasons=[
                    f"ROE={roe:.1f}% (deteriorating)",
                    f"PE={pe:.1f} not cheap enough to compensate",
                ],
                strategy_name=self.name,
            )

        return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
