"""Technical analysis snapshot model – persisted computed indicators."""
from __future__ import annotations

from sqlalchemy import Float, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TechnicalSnapshot(BaseModel):
    """Computed technical indicators for a stock at a point in time."""
    __tablename__ = "technical_snapshots"

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Moving averages
    ma5: Mapped[float] = mapped_column(Float, default=0.0)
    ma10: Mapped[float] = mapped_column(Float, default=0.0)
    ma20: Mapped[float] = mapped_column(Float, default=0.0)
    ma60: Mapped[float] = mapped_column(Float, default=0.0)
    ema12: Mapped[float] = mapped_column(Float, default=0.0)
    ema26: Mapped[float] = mapped_column(Float, default=0.0)

    # MACD
    macd_line: Mapped[float] = mapped_column(Float, default=0.0)
    macd_signal: Mapped[float] = mapped_column(Float, default=0.0)
    macd_histogram: Mapped[float] = mapped_column(Float, default=0.0)

    # RSI
    rsi: Mapped[float] = mapped_column(Float, default=0.0)

    # KDJ
    kdj_k: Mapped[float] = mapped_column(Float, default=0.0)
    kdj_d: Mapped[float] = mapped_column(Float, default=0.0)
    kdj_j: Mapped[float] = mapped_column(Float, default=0.0)

    # Bollinger
    boll_upper: Mapped[float] = mapped_column(Float, default=0.0)
    boll_middle: Mapped[float] = mapped_column(Float, default=0.0)
    boll_lower: Mapped[float] = mapped_column(Float, default=0.0)

    # ATR
    atr: Mapped[float] = mapped_column(Float, default=0.0)

    # Volume
    volume_ma5: Mapped[float] = mapped_column(Float, default=0.0)
    volume_ma10: Mapped[float] = mapped_column(Float, default=0.0)
    volume_ma20: Mapped[float] = mapped_column(Float, default=0.0)

    # Derived
    volatility: Mapped[float] = mapped_column(Float, default=0.0)
    turnover_rate: Mapped[float] = mapped_column(Float, default=0.0)
    amplitude: Mapped[float] = mapped_column(Float, default=0.0)

    # Metadata
    period: Mapped[int] = mapped_column(Integer, default=0)  # Number of bars used
    data_source: Mapped[str] = mapped_column(String(20), default="unknown")
