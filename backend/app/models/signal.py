"""AI/Strategy signal model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Signal(BaseModel):
    """Generated signal from AI or strategy."""
    __tablename__ = "signals"

    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY | SELL | HOLD
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # AI | STRATEGY | MANUAL
    score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    entry_price: Mapped[float | None] = mapped_column(Float)
    stop_loss: Mapped[float | None] = mapped_column(Float)
    take_profit: Mapped[float | None] = mapped_column(Float)
    position_target: Mapped[float | None] = mapped_column(Float)
    strategy_name: Mapped[str | None] = mapped_column(String(50))
    agent_name: Mapped[str | None] = mapped_column(String(50))
    reasons: Mapped[dict | None] = mapped_column(JSONB)
    risks: Mapped[dict | None] = mapped_column(JSONB)
    bull_case: Mapped[str | None] = mapped_column(Text)
    base_case: Mapped[str | None] = mapped_column(Text)
    bear_case: Mapped[str | None] = mapped_column(Text)
    data_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signal_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE | EXPIRED | EXECUTED
    version: Mapped[str] = mapped_column(String(20), default="v1")
