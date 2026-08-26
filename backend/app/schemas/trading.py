"""Trading-related schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    """Create a new order."""
    symbol: str
    side: str  # BUY | SELL
    order_type: str = "LIMIT"
    price: Optional[float] = None
    quantity: int = Field(ge=100, description="Must be a multiple of 100 for A-shares")
    strategy_name: Optional[str] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    signal_id: Optional[UUID] = None


class OrderResponse(BaseModel):
    id: UUID
    account_id: UUID
    symbol: str
    side: str
    order_type: str
    price: Optional[float]
    quantity: int
    filled_quantity: int
    avg_fill_price: Optional[float]
    status: str
    client_order_id: str
    strategy_name: Optional[str]
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TradeProposal(BaseModel):
    """AI-generated trade proposal requiring human confirmation."""
    symbol: str
    direction: str  # BUY | SELL
    price: float
    quantity: int
    amount: float
    stop_loss: float
    take_profit: float
    strategy: str
    confidence: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=100.0)
    reasons: List[str] = []
    risks: List[str] = []
    bull_case: Optional[str] = None
    base_case: Optional[str] = None
    bear_case: Optional[str] = None
    invalidation: Optional[str] = None
    holding_period: Optional[str] = None
    data_timestamp: Optional[datetime] = None


class TradeConfirm(BaseModel):
    """Confirm or reject a trade proposal."""
    order_id: UUID
    action: str  # CONFIRM | REJECT
    reason: Optional[str] = None


class PositionResponse(BaseModel):
    id: UUID
    symbol: str
    quantity: int
    available_quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float
    is_open: bool

    class Config:
        from_attributes = True


class AccountSummary(BaseModel):
    id: UUID
    name: str
    account_type: str
    cash: float
    total_asset: float
    realized_pnl: float
    unrealized_pnl: float = 0.0
    position_count: int = 0
    positions: List[PositionResponse] = []


class PortfolioRisk(BaseModel):
    """Portfolio-level risk summary."""
    total_asset: float
    cash: float
    market_value: float
    position_ratio: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    daily_pnl: float
    daily_pnl_pct: float
    industry_exposures: dict = {}
    top_positions: list = []
    risk_events: list = []
