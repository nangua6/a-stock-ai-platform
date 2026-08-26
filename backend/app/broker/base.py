"""Abstract broker adapter interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class AccountInfo:
    account_id: str
    total_asset: float = 0.0
    cash: float = 0.0
    market_value: float = 0.0
    frozen_cash: float = 0.0
    available_cash: float = 0.0


@dataclass
class PositionInfo:
    symbol: str
    quantity: int = 0
    available_quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class OrderRequest:
    symbol: str
    side: str  # BUY | SELL
    order_type: str = "LIMIT"
    price: Optional[float] = None
    quantity: int = 0
    client_order_id: str = ""
    strategy_name: Optional[str] = None


@dataclass
class OrderResult:
    success: bool = False
    broker_order_id: str = ""
    message: str = ""
    error_code: str = ""
    timestamp: Optional[datetime] = None


@dataclass
class OrderInfo:
    broker_order_id: str = ""
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    price: float = 0.0
    quantity: int = 0
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    status: str = ""
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None


@dataclass
class TradeInfo:
    broker_trade_id: str = ""
    broker_order_id: str = ""
    symbol: str = ""
    side: str = ""
    price: float = 0.0
    quantity: int = 0
    amount: float = 0.0
    commission: float = 0.0
    trade_time: Optional[datetime] = None


class BrokerAdapter(ABC):
    """
    Abstract broker adapter.

    All broker implementations (Mock, Paper, QMT, PTrade) must implement this interface.
    The system NEVER calls a broker API directly; everything goes through this adapter.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Broker name identifier."""
        ...

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """Return account summary (cash, asset, market value)."""
        ...

    @abstractmethod
    async def get_positions(self) -> List[PositionInfo]:
        """Return all open positions."""
        ...

    @abstractmethod
    async def get_orders(self, status: Optional[str] = None) -> List[OrderInfo]:
        """Return orders, optionally filtered by status."""
        ...

    @abstractmethod
    async def get_trades(self, order_id: Optional[str] = None) -> List[TradeInfo]:
        """Return trade fills, optionally for a specific order."""
        ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> dict:
        """Return real-time quote for a symbol."""
        ...

    @abstractmethod
    async def place_order(self, request: OrderRequest) -> OrderResult:
        """Submit an order to the broker."""
        ...

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> OrderResult:
        """Cancel a pending order."""
        ...

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> OrderInfo:
        """Query order status."""
        ...
