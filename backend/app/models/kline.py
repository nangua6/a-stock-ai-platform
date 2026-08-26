"""K-line (OHLCV) data model."""
from __future__ import annotations

from sqlalchemy import BigInteger, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Kline(BaseModel):
    """OHLCV kline bar for any timeframe."""
    __tablename__ = "klines"

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="D")  # D | 1 | 5 | 15 | 30 | 60
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    turnover: Mapped[float] = mapped_column(Float, default=0.0)
    amplitude: Mapped[float | None] = mapped_column(Float)
    change_pct: Mapped[float | None] = mapped_column(Float)
    change_amount: Mapped[float | None] = mapped_column(Float)
    data_source: Mapped[str] = mapped_column(String(20), default="unknown")
    available_time: Mapped[str | None] = mapped_column(String(30))

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", "timeframe", name="uq_kline_symbol_date_tf"),
        {"comment": "OHLCV candlestick data with time granularity"},
    )
