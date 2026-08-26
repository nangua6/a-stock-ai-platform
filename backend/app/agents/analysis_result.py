"""
Structured stock analysis result types.

All AI analysis output MUST use these types. No free-text-only outputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


class Recommendation(str, Enum):
    WATCH = "WATCH"
    BUY_CANDIDATE = "BUY_CANDIDATE"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    AVOID = "AVOID"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class TrendDirection(str, Enum):
    STRONG_UP = "STRONG_UP"
    UP = "UP"
    SIDEWAYS = "SIDEWAYS"
    DOWN = "DOWN"
    STRONG_DOWN = "STRONG_DOWN"


class DataQuality(str, Enum):
    GOOD = "GOOD"
    STALE = "STALE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class TechnicalScore:
    """Deterministic technical analysis score."""
    trend: TrendDirection = TrendDirection.SIDEWAYS
    momentum: float = 0.0       # -1.0 to 1.0
    volume_signal: float = 0.0  # -1.0 to 1.0
    ma_alignment: float = 0.0   # -1.0 to 1.0 (MA5/10/20 alignment)
    rsi_signal: float = 0.0     # -1.0 (oversold) to 1.0 (overbought)
    macd_signal: float = 0.0    # -1.0 to 1.0
    score: float = 0.0          # 0-100 composite

    def to_dict(self) -> dict:
        return {
            "trend": self.trend.value,
            "momentum": round(self.momentum, 3),
            "volume_signal": round(self.volume_signal, 3),
            "ma_alignment": round(self.ma_alignment, 3),
            "rsi_signal": round(self.rsi_signal, 3),
            "macd_signal": round(self.macd_signal, 3),
            "score": round(self.score, 1),
        }


@dataclass
class RiskAssessment:
    """Deterministic risk assessment."""
    volatility: float = 0.0
    max_drawdown: float = 0.0
    data_age_seconds: float = 0.0
    is_data_fresh: bool = True
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH, EXTREME
    key_risks: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "volatility": round(self.volatility, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "data_age_seconds": round(self.data_age_seconds, 1),
            "is_data_fresh": self.is_data_fresh,
            "risk_level": self.risk_level,
            "key_risks": self.key_risks,
        }


@dataclass
class StockAnalysisResult:
    """
    Structured stock analysis output.

    Every field is typed and bounded. No ambiguous free-text as system output.
    """
    # Identity
    symbol: str = ""
    name: str = ""
    analysis_timestamp: str = ""
    data_timestamp: str = ""

    # Quote snapshot (from real quote data, NOT from scores)
    current_price: Optional[float] = None   # None = unavailable
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    amount: Optional[float] = None

    # Scores
    technical: TechnicalScore = field(default_factory=TechnicalScore)
    fundamental_score: float = 0.0  # 0-100
    risk: RiskAssessment = field(default_factory=RiskAssessment)
    overall_score: float = 0.0      # 0-100

    # Recommendation
    recommendation: Recommendation = Recommendation.DATA_UNAVAILABLE
    confidence: float = 0.0         # 0.0 to 1.0

    # Analysis text (from LLM or deterministic)
    bull_case: str = ""
    bear_case: str = ""
    key_risks: List[str] = field(default_factory=list)

    # Data quality
    data_quality: DataQuality = DataQuality.GOOD
    data_source: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "analysis_timestamp": self.analysis_timestamp,
            "data_timestamp": self.data_timestamp,
            "current_price": self.current_price,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "amount": self.amount,
            "technical": self.technical.to_dict(),
            "fundamental_score": round(self.fundamental_score, 1),
            "risk": self.risk.to_dict(),
            "overall_score": round(self.overall_score, 1),
            "recommendation": self.recommendation.value,
            "confidence": round(self.confidence, 3),
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "key_risks": self.key_risks,
            "data_quality": self.data_quality.value,
            "data_source": self.data_source,
        }
