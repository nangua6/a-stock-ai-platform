"""Trading account model."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Account(BaseModel):
    """Trading account – one user may have multiple accounts (paper, live)."""
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default="PAPER")  # PAPER | LIVE
    broker: Mapped[str] = mapped_column(String(30), nullable=False, default="mock")

    # Cash & portfolio state (denormalized for fast reads)
    initial_capital: Mapped[float] = mapped_column(Float, default=1000000.0, nullable=False)
    cash: Mapped[float] = mapped_column(Float, default=1000000.0, nullable=False)
    total_asset: Mapped[float] = mapped_column(Float, default=1000000.0, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="accounts", lazy="selectin")
    positions = relationship("Position", back_populates="account", lazy="selectin")
    orders = relationship("Order", back_populates="account", lazy="selectin")
    trades = relationship("Trade", back_populates="account", lazy="selectin")
