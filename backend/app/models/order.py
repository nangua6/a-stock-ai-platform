"""Order model with full A-share trading rule awareness."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class OrderSide(str, PyEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, PyEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, PyEnum):
    PENDING = "PENDING"           # Created, awaiting risk check
    RISK_REJECTED = "RISK_REJECTED"
    PENDING_CONFIRM = "PENDING_CONFIRM"  # Awaiting human confirmation
    SUBMITTED = "SUBMITTED"       # Sent to broker
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class Order(BaseModel):
    """An order record – paper or live."""
    __tablename__ = "orders"

    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY | SELL
    order_type: Mapped[str] = mapped_column(String(10), nullable=False, default="LIMIT")
    price: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    filled_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_fill_price: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING.value, nullable=False, index=True)
    client_order_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    broker_order_id: Mapped[str | None] = mapped_column(String(50))

    # Metadata
    strategy_name: Mapped[str | None] = mapped_column(String(50))
    signal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    risk_check_result: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    # A-share specific
    is_t1_restricted: Mapped[bool] = mapped_column(default=False)  # T+1 buy restriction
    stop_loss_price: Mapped[float | None] = mapped_column(Float)
    take_profit_price: Mapped[float | None] = mapped_column(Float)

    # Timestamps
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    account = relationship("Account", back_populates="orders", lazy="selectin")
    trades = relationship("Trade", back_populates="order", lazy="selectin")
