"""Trade (fill) model – each trade represents a filled portion of an order."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Trade(BaseModel):
    """Individual trade execution (fill)."""
    __tablename__ = "trades"

    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # price * quantity
    commission: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    stamp_tax: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    transfer_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    slippage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    broker_trade_id: Mapped[str | None] = mapped_column(String(50))
    trade_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    account = relationship("Account", back_populates="trades", lazy="selectin")
    order = relationship("Order", back_populates="trades", lazy="selectin")
