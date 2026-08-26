"""Analysis snapshot model – combines quote + technical + risk into structured output."""
from __future__ import annotations

from sqlalchemy import Float, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AnalysisSnapshot(BaseModel):
    """Deterministic analysis result for a stock at a point in time."""
    __tablename__ = "analysis_snapshots"

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), default="")
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Quote snapshot
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    change_pct: Mapped[float] = mapped_column(Float, default=0.0)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)

    # Scores
    technical_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    fundamental_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100

    # Recommendation
    recommendation: Mapped[str] = mapped_column(String(20), default="DATA_UNAVAILABLE")
    # WATCH | BUY_CANDIDATE | HOLD | REDUCE | AVOID | DATA_UNAVAILABLE
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1

    # Technical detail (JSON)
    technical_detail: Mapped[dict | None] = mapped_column(JSON)

    # Risk
    risk_level: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    risk_details: Mapped[dict | None] = mapped_column(JSON)

    # Analysis text
    bull_case: Mapped[str | None] = mapped_column(Text)
    bear_case: Mapped[str | None] = mapped_column(Text)
    key_risks: Mapped[dict | None] = mapped_column(JSON)

    # Data quality
    data_quality: Mapped[str] = mapped_column(String(20), default="GOOD")
    data_source: Mapped[str] = mapped_column(String(20), default="unknown")
