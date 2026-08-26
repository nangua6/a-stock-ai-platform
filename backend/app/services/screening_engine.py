"""
Stock Screening Engine – filter stocks by structured rules.

All rules are deterministic and data-driven. No LLM calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.market.base import KlineData, QuoteData, TechnicalIndicators
from app.services.technical_analysis import TechnicalAnalysisService
from app.core.logging import get_logger

logger = get_logger("screening")


class FactorDirection(str, Enum):
    """Whether higher or lower values are preferred."""
    HIGHER = "higher"
    LOWER = "lower"


@dataclass
class ScreeningRule:
    """A single screening rule."""
    name: str
    factor: str               # Which factor to evaluate
    direction: FactorDirection = FactorDirection.HIGHER
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    weight: float = 1.0       # For scoring


@dataclass
class CandidateStock:
    """A stock that passed screening criteria."""
    symbol: str = ""
    name: str = ""
    score: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)
    matched_rules: List[str] = field(default_factory=list)
    data_source: str = ""


@dataclass
class ScreeningResult:
    """Result of a screening run."""
    candidates: List[CandidateStock] = field(default_factory=list)
    total_screened: int = 0
    total_passed: int = 0
    rules_applied: int = 0
    timestamp: str = ""
    data_source: str = ""


class ScreeningEngine:
    """
    Stock screening engine.

    Evaluates stocks against structured factor rules and returns ranked candidates.
    """

    def __init__(self):
        self.ta_service = TechnicalAnalysisService()

    def compute_factors(
        self,
        quote: QuoteData,
        klines: List[KlineData],
    ) -> Dict[str, float]:
        """
        Compute screening factors from quote and kline data.

        Returns a dict of factor_name -> value.
        """
        factors: Dict[str, float] = {}

        # Quote-based factors
        if quote and quote.price > 0:
            factors["price"] = quote.price
            factors["change_pct"] = quote.change_pct
            factors["volume"] = float(quote.volume)
            factors["amount"] = quote.amount
            if quote.pre_close > 0:
                factors["amplitude"] = (quote.high - quote.low) / quote.pre_close * 100

        # Kline-based factors (need at least 5 bars)
        if klines and len(klines) >= 5:
            closes = [k.close for k in klines]
            volumes = [float(k.volume) for k in klines]

            # Volume ratio (量比): today vol / avg 5-day vol
            if len(volumes) >= 6:
                avg_5 = sum(volumes[-6:-1]) / 5
                if avg_5 > 0:
                    factors["volume_ratio"] = volumes[-1] / avg_5

            # Recent momentum: 5-day return
            if len(closes) >= 6 and closes[-6] > 0:
                factors["momentum_5d"] = (closes[-1] / closes[-6] - 1) * 100

            # Recent momentum: 20-day return
            if len(closes) >= 21 and closes[-21] > 0:
                factors["momentum_20d"] = (closes[-1] / closes[-21] - 1) * 100

            # Technical indicators
            try:
                ta = self.ta_service.compute(klines)
                factors["ma5"] = ta.ma5
                factors["ma10"] = ta.ma10
                factors["ma20"] = ta.ma20
                factors["rsi"] = ta.rsi
                factors["macd_histogram"] = ta.macd_histogram
                factors["volatility"] = ta.volatility
                factors["atr"] = ta.atr
                factors["turnover_rate"] = ta.turnover_rate

                # MA trend: price > ma5 > ma10 > ma20
                if ta.ma5 > 0 and ta.ma10 > 0 and ta.ma20 > 0:
                    factors["ma_trend"] = 1.0 if (
                        closes[-1] > ta.ma5 > ta.ma10 > ta.ma20
                    ) else 0.0

            except Exception as e:
                logger.warning("screening_ta_failed", error=str(e)[:100])

        return factors

    def screen(
        self,
        candidates: List[Dict[str, Any]],
        rules: List[ScreeningRule],
        top_n: int = 20,
    ) -> ScreeningResult:
        """
        Screen a list of stock data against rules.

        Each candidate dict must have: symbol, name, quote (QuoteData), klines (List[KlineData]).
        """
        passed = []
        for cand in candidates:
            symbol = cand.get("symbol", "")
            name = cand.get("name", "")
            quote = cand.get("quote")
            klines = cand.get("klines", [])

            factors = self.compute_factors(quote, klines)
            if not factors:
                continue

            matched = []
            score = 0.0
            all_pass = True

            for rule in rules:
                value = factors.get(rule.factor)
                if value is None:
                    all_pass = False
                    continue

                # Check min/max bounds
                if rule.min_value is not None and value < rule.min_value:
                    all_pass = False
                    continue
                if rule.max_value is not None and value > rule.max_value:
                    all_pass = False
                    continue

                matched.append(rule.name)
                # Score: normalize and weight
                if rule.direction == FactorDirection.HIGHER:
                    score += abs(value) * rule.weight
                else:
                    score += (1.0 / max(abs(value), 0.01)) * rule.weight

            if all_pass and matched:
                passed.append(CandidateStock(
                    symbol=symbol,
                    name=name,
                    score=round(score, 4),
                    factors=factors,
                    matched_rules=matched,
                    data_source=quote.data_source if quote else "",
                ))

        # Sort by score descending
        passed.sort(key=lambda c: c.score, reverse=True)

        return ScreeningResult(
            candidates=passed[:top_n],
            total_screened=len(candidates),
            total_passed=len(passed),
            rules_applied=len(rules),
            timestamp="",
            data_source="",
        )
