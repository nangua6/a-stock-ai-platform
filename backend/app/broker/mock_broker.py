"""Mock broker – always succeeds, used for development and unit tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.broker.base import (
    AccountInfo,
    BrokerAdapter,
    OrderInfo,
    OrderRequest,
    OrderResult,
    PositionInfo,
    TradeInfo,
)


class MockBroker(BrokerAdapter):
    """Mock broker that always succeeds – no real money or market constraints."""

    def __init__(self):
        self._orders: dict[str, OrderInfo] = {}
        self._trades: list[TradeInfo] = []
        self._positions: dict[str, PositionInfo] = {}
        self._cash: float = 1_000_000.0

    @property
    def name(self) -> str:
        return "mock"

    async def get_account(self) -> AccountInfo:
        market_value = sum(p.market_value for p in self._positions.values())
        return AccountInfo(
            account_id="mock-001",
            total_asset=self._cash + market_value,
            cash=self._cash,
            market_value=market_value,
            frozen_cash=0.0,
            available_cash=self._cash,
        )

    async def get_positions(self) -> List[PositionInfo]:
        return list(self._positions.values())

    async def get_orders(self, status: Optional[str] = None) -> List[OrderInfo]:
        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return orders

    async def get_trades(self, order_id: Optional[str] = None) -> List[TradeInfo]:
        if order_id:
            return [t for t in self._trades if t.broker_order_id == order_id]
        return list(self._trades)

    async def get_quote(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "price": 100.0,  # Mock always returns 100
            "bid": 99.9,
            "ask": 100.1,
            "volume": 1_000_000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def place_order(self, request: OrderRequest) -> OrderResult:
        broker_order_id = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc)

        order_info = OrderInfo(
            broker_order_id=broker_order_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            price=request.price or 100.0,
            quantity=request.quantity,
            filled_quantity=request.quantity,
            avg_fill_price=request.price or 100.0,
            status="FILLED",
            created_at=now,
            filled_at=now,
        )
        self._orders[broker_order_id] = order_info

        # Record a fill
        trade = TradeInfo(
            broker_trade_id=f"MT-{uuid.uuid4().hex[:8].upper()}",
            broker_order_id=broker_order_id,
            symbol=request.symbol,
            side=request.side,
            price=request.price or 100.0,
            quantity=request.quantity,
            amount=(request.price or 100.0) * request.quantity,
            commission=0.0,
            trade_time=now,
        )
        self._trades.append(trade)

        # Update mock positions
        pos = self._positions.get(request.symbol)
        if request.side == "BUY":
            cost = (request.price or 100.0) * request.quantity
            self._cash -= cost
            if pos:
                total_qty = pos.quantity + request.quantity
                pos.avg_cost = (pos.avg_cost * pos.quantity + cost) / total_qty
                pos.quantity = total_qty
                pos.available_quantity = total_qty
                pos.market_value = pos.current_price * total_qty
            else:
                self._positions[request.symbol] = PositionInfo(
                    symbol=request.symbol,
                    quantity=request.quantity,
                    available_quantity=request.quantity,
                    avg_cost=request.price or 100.0,
                    current_price=request.price or 100.0,
                    market_value=(request.price or 100.0) * request.quantity,
                )
        elif request.side == "SELL" and pos:
            revenue = (request.price or 100.0) * request.quantity
            self._cash += revenue
            pos.quantity -= request.quantity
            pos.available_quantity = pos.quantity
            pos.market_value = pos.current_price * pos.quantity
            if pos.quantity <= 0:
                del self._positions[request.symbol]

        return OrderResult(
            success=True,
            broker_order_id=broker_order_id,
            message="Mock order filled",
            timestamp=now,
        )

    async def cancel_order(self, broker_order_id: str) -> OrderResult:
        order = self._orders.get(broker_order_id)
        if order:
            order.status = "CANCELLED"
        return OrderResult(
            success=True,
            broker_order_id=broker_order_id,
            message="Mock order cancelled",
        )

    async def get_order_status(self, broker_order_id: str) -> OrderInfo:
        order = self._orders.get(broker_order_id)
        if not order:
            return OrderInfo(broker_order_id=broker_order_id, status="NOT_FOUND")
        return order
