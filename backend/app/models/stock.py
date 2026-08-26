"""Stock metadata model."""
from __future__ import annotations

from sqlalchemy import Boolean, Float, String, Date, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Stock(BaseModel):
    """A-share stock metadata (cached from market data provider)."""
    __tablename__ = "stocks"

    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # e.g. 600519.SH
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # SH | SZ | BJ
    board: Mapped[str | None] = mapped_column(String(20))  # MAIN | GEM | STAR | BSE
    industry: Mapped[str | None] = mapped_column(String(50))
    industry_code: Mapped[str | None] = mapped_column(String(20))
    area: Mapped[str | None] = mapped_column(String(50))
    list_date: Mapped[str | None] = mapped_column(String(10))
    is_st: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Latest quote snapshot (updated by market data service)
    latest_price: Mapped[float | None] = mapped_column(Float)
    latest_volume: Mapped[int | None] = mapped_column(BigInteger)
    latest_amount: Mapped[float | None] = mapped_column(Float)
    latest_update: Mapped[str | None] = mapped_column(String(30))
