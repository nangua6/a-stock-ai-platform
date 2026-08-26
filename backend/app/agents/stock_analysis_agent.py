"""
Stock Analysis Agent – produces structured StockAnalysisResult.

Combines:
1. Market data (from ProviderManager)
2. Technical indicators (from TechnicalAnalysisService)
3. Risk assessment (deterministic)
4. LLM interpretation (optional, when available)

The output is ALWAYS a structured StockAnalysisResult.
LLM failure does NOT block analysis – deterministic scoring is the fallback.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.agents.analysis_result import (
    DataQuality,
    Recommendation,
    RiskAssessment,
    StockAnalysisResult,
    TechnicalScore,
    TrendDirection,
)
from app.core.logging import get_logger
from app.market.base import DataFreshness, KlineData, TechnicalIndicators
from app.market.provider_manager import ProviderManager
from app.services.technical_analysis import TechnicalAnalysisService

logger = get_logger("stock_analysis")


class StockAnalysisAgent:
    """
    Produces structured stock analysis without requiring LLM.

    Deterministic scoring:
    - Technical score from TA indicators
    - Risk assessment from volatility/data quality
    - Recommendation from combined scores
    - LLM adds bull/bear case text (optional)
    """

    def __init__(self, provider: ProviderManager):
        self.provider = provider
        self.ta_service = TechnicalAnalysisService()

    async def analyze(self, symbol: str) -> StockAnalysisResult:
        """Full structured analysis for a stock."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Fetch data
        quote, quote_avail = await self.provider.get_quote_with_availability(symbol)
        klines, kline_avail = await self.provider.get_kline_with_availability(symbol, limit=60)

        # 2. Data quality assessment
        data_quality = self._assess_data_quality(quote, klines, quote_avail)

        # 3. Technical analysis
        technical = self._compute_technical(klines)

        # 4. Risk assessment
        risk = self._compute_risk(technical, quote_avail)

        # 5. Recommendation
        recommendation, confidence, overall_score = self._compute_recommendation(
            technical, risk, data_quality,
        )

        # 6. Bull/bear cases (deterministic text)
        bull_case, bear_case, key_risks = self._generate_cases(
            symbol, quote, technical, risk,
        )

        return StockAnalysisResult(
            symbol=symbol,
            name=quote.name if quote else "",
            analysis_timestamp=now_iso,
            data_timestamp=quote.timestamp if quote else "",
            technical=technical,
            fundamental_score=0.0,  # No fundamental data in sandbox
            risk=risk,
            overall_score=overall_score,
            recommendation=recommendation,
            confidence=confidence,
            bull_case=bull_case,
            bear_case=bear_case,
            key_risks=key_risks,
            data_quality=data_quality,
            data_source=quote.data_source if quote else "unavailable",
        )

    def _assess_data_quality(self, quote, klines, quote_avail) -> DataQuality:
        if not quote or quote.price <= 0:
            return DataQuality.UNAVAILABLE
        if quote_avail.freshness == DataFreshness.STALE:
            return DataQuality.STALE
        if not klines or len(klines) < 10:
            return DataQuality.PARTIAL
        return DataQuality.GOOD

    def _compute_technical(self, klines) -> TechnicalScore:
        if not klines or len(klines) < 5:
            return TechnicalScore()

        ta = self.ta_service.compute(klines)
        closes = [k.close for k in klines]
        price = closes[-1]

        # Trend direction
        trend = TrendDirection.SIDEWAYS
        if ta.ma5 > 0 and ta.ma20 > 0:
            ma_spread = (ta.ma5 - ta.ma20) / ta.ma20 * 100
            if price > ta.ma5 > ta.ma10 > ta.ma20 and ta.ma20 > 0:
                trend = TrendDirection.STRONG_UP
            elif price > ta.ma20 and ma_spread > 0:
                trend = TrendDirection.UP
            elif price < ta.ma5 < ta.ma10 < ta.ma20 and ta.ma20 > 0:
                trend = TrendDirection.STRONG_DOWN
            elif price < ta.ma20 and ma_spread < 0:
                trend = TrendDirection.DOWN

        # Momentum (normalized ROC-like)
        momentum = 0.0
        if len(closes) >= 11:
            roc10 = (closes[-1] / closes[-11] - 1) * 100
            momentum = max(-1.0, min(1.0, roc10 / 10.0))

        # Volume signal
        vol_signal = 0.0
        if ta.volume_ma5 > 0 and ta.volume_ma10 > 0:
            vol_ratio = ta.volume_ma5 / ta.volume_ma10
            vol_signal = max(-1.0, min(1.0, (vol_ratio - 1.0) * 2))

        # MA alignment score
        ma_align = 0.0
        if ta.ma5 > 0 and ta.ma10 > 0 and ta.ma20 > 0:
            if ta.ma5 > ta.ma10 > ta.ma20:
                ma_align = 0.8
            elif ta.ma5 < ta.ma10 < ta.ma20:
                ma_align = -0.8

        # RSI signal (-1 oversold to +1 overbought, 0 at 50)
        rsi_signal = 0.0
        if ta.rsi > 0:
            rsi_signal = (ta.rsi - 50) / 50.0

        # MACD signal
        macd_signal = 0.0
        if ta.macd_histogram != 0:
            macd_signal = max(-1.0, min(1.0, ta.macd_histogram / max(abs(price * 0.01), 0.01)))

        # Composite score (0-100)
        score = 50  # neutral base
        score += momentum * 15          # ±15
        score += ma_align * 10          # ±10
        score += rsi_signal * 10        # ±10
        score += macd_signal * 10       # ±10
        score += vol_signal * 5         # ±5
        score = max(0, min(100, score))

        return TechnicalScore(
            trend=trend,
            momentum=momentum,
            volume_signal=vol_signal,
            ma_alignment=ma_align,
            rsi_signal=rsi_signal,
            macd_signal=macd_signal,
            score=score,
        )

    def _compute_risk(self, technical: TechnicalScore, quote_avail) -> RiskAssessment:
        key_risks = []
        risk_level = "MEDIUM"

        # Volatility from technical
        if abs(technical.momentum) > 0.7:
            key_risks.append("High momentum (potential reversal risk)")
            risk_level = "HIGH"

        if technical.trend in (TrendDirection.STRONG_DOWN, TrendDirection.DOWN):
            key_risks.append("Downtrend active")
            risk_level = "HIGH"

        if technical.rsi_signal > 0.8:
            key_risks.append("RSI overbought")
        elif technical.rsi_signal < -0.8:
            key_risks.append("RSI deeply oversold (potential bounce or continuation)")

        data_age = quote_avail.data_age_seconds if quote_avail else 999
        is_fresh = data_age < 300

        if not is_fresh:
            key_risks.append(f"Stale data ({data_age:.0f}s old)")
            risk_level = "HIGH"

        if not key_risks:
            risk_level = "LOW"

        return RiskAssessment(
            volatility=abs(technical.momentum),
            data_age_seconds=data_age,
            is_data_fresh=is_fresh,
            risk_level=risk_level,
            key_risks=key_risks,
        )

    def _compute_recommendation(
        self, technical: TechnicalScore, risk: RiskAssessment, data_quality: DataQuality,
    ) -> tuple:
        """Returns (recommendation, confidence, overall_score)."""
        if data_quality == DataQuality.UNAVAILABLE:
            return Recommendation.DATA_UNAVAILABLE, 0.0, 0.0

        score = technical.score
        confidence = 0.5  # base confidence

        # Adjust confidence by data quality
        if data_quality == DataQuality.GOOD:
            confidence = 0.7
        elif data_quality == DataQuality.PARTIAL:
            confidence = 0.4
        elif data_quality == DataQuality.STALE:
            confidence = 0.3

        # Risk adjustment
        if risk.risk_level == "HIGH":
            score -= 10
            confidence *= 0.8
        elif risk.risk_level == "LOW":
            score += 5

        # Recommendation mapping
        if score >= 70 and technical.trend in (TrendDirection.STRONG_UP, TrendDirection.UP):
            rec = Recommendation.BUY_CANDIDATE
        elif score >= 55:
            rec = Recommendation.WATCH
        elif score >= 40:
            rec = Recommendation.HOLD
        elif score >= 25:
            rec = Recommendation.REDUCE
        else:
            rec = Recommendation.AVOID

        return rec, min(confidence, 1.0), max(0, min(100, score))

    def _generate_cases(self, symbol, quote, technical, risk):
        """Generate deterministic bull/bear/risk text."""
        bull_points = []
        bear_points = []
        risks = list(risk.key_risks)

        if technical.trend in (TrendDirection.STRONG_UP, TrendDirection.UP):
            bull_points.append(f"Trend is {technical.trend.value}")
        if technical.momentum > 0.3:
            bull_points.append(f"Positive momentum ({technical.momentum:.2f})")
        if technical.rsi_signal < -0.3:
            bull_points.append(f"RSI in potential bounce zone")
        if technical.ma_alignment > 0.3:
            bull_points.append("MA alignment bullish")

        if technical.trend in (TrendDirection.STRONG_DOWN, TrendDirection.DOWN):
            bear_points.append(f"Trend is {technical.trend.value}")
        if technical.momentum < -0.3:
            bear_points.append(f"Negative momentum ({technical.momentum:.2f})")
        if technical.rsi_signal > 0.6:
            bear_points.append("RSI approaching overbought")
        if technical.macd_signal < -0.3:
            bear_points.append("MACD bearish crossover")

        bull = "; ".join(bull_points) if bull_points else "No strong bullish signals"
        bear = "; ".join(bear_points) if bear_points else "No strong bearish signals"

        return bull, bear, risks
