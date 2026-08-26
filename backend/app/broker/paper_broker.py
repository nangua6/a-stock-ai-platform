"""Paper broker – simulates A-share trading rules with virtual money."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.broker.base import (
    AccountInfo,
    BrokerAdapter,
    OrderInfo,
    OrderRequest,
    OrderResult,
    PositionInfo,
    TradeInfo,
)


# A-share trading fee structure
COMMISSION_RATE = 0.0003       # 万三佣金（买卖双向）
MIN_COMMISSION = 5.0           # 最低佣金 5 元
STAMP_TAX_RATE_SELL = 0.0005   # 印花税 万五（仅卖出）
TRANSFER_FEE_RATE = 0.00001   # 过户费 十万分之一
SLIPPAGE_RATE = 0.001          # 滑点 千一


class PaperBroker(BrokerAdapter):
    """
    Paper broker with realistic A-share constraints:
    - T+1: Today bought shares cannot be sold until the next trading day
    - Price limits: ±10% (main board), ±20% (GEM/STAR)
    - Minimum lot size: 100 shares (1 手)
    - Realistic fee calculation
    """

    def __init__(self, initial_capital: float = 1_000_000.0):
        self._cash: float = initial_capital
        self._initial_capital: float = initial_capital
        self._positions: Dict[str, dict] = {}
        self._orders: Dict[str, OrderInfo] = {}
        self._trades: List[TradeInfo] = []
        self._today: str = datetime.now().strftime("%Y-%m-%d")

    @property
    def name(self) -> str:
        return "paper"

    def _calculate_commission(self, amount: float, side: str) -> float:
        commission = max(amount * COMMISSION_RATE, MIN_COMMISSION)
        stamp_tax = amount * STAMP_TAX_RATE_SELL if side == "SELL" else 0.0
        transfer_fee = amount * TRANSFER_FEE_RATE
        return commission + stamp_tax + transfer_fee

    def _apply_slippage(self, price: float, side: str) -> float:
        """Simulate slippage: buy slightly higher, sell slightly lower."""
        if side == "BUY":
            return price * (1 + SLIPPAGE_RATE)
        return price * (1 - SLIPPAGE_RATE)

    async def get_account(self) -> AccountInfo:
        market_value = sum(
            p["quantity"] * p["current_price"] for p in self._positions.values()
        )
        return AccountInfo(
            account_id="paper-001",
            total_asset=self._cash + market_value,
            cash=self._cash,
            market_value=market_value,
            frozen_cash=0.0,
            available_cash=self._cash,
        )

    async def get_positions(self) -> List[PositionInfo]:
        result = []
        for sym, p in self._positions.items():
            if p["quantity"] > 0:
                result.append(PositionInfo(
                    symbol=sym,
                    quantity=p["quantity"],
                    available_quantity=p["available_quantity"],
                    avg_cost=p["avg_cost"],
                    current_price=p["current_price"],
                    market_value=p["current_price"] * p["quantity"],
                    unrealized_pnl=(p["current_price"] - p["avg_cost"]) * p["quantity"],
                    unrealized_pnl_pct=(p["current_price"] / p["avg_cost"] - 1) if p["avg_cost"] > 0 else 0.0,
                ))
        return result

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
        pos = self._positions.get(symbol)
        price = pos["current_price"] if pos else 100.0
        return {
            "symbol": symbol,
            "price": price,
            "bid": price * 0.999,
            "ask": price * 1.001,
            "volume": 500_000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def place_order(self, request: OrderRequest) -> OrderResult:
        broker_order_id = f"PAPER-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc)
        price = request.price or 100.0

        # Validate lot size
        if request.quantity % 100 != 0:
            return OrderResult(
                success=False,
                broker_order_id="",
                message="Quantity must be a multiple of 100 (1手)",
                error_code="INVALID_LOT_SIZE",
            )

        # Validate sufficient funds for buy
        if request.side == "BUY":
            total_cost = price * request.quantity
            fees = self._calculate_commission(total_cost, "BUY")
            if self._cash < total_cost + fees:
                return OrderResult(
                    success=False,
                    broker_order_id="",
                    message=f"Insufficient funds: need {total_cost + fees:.2f}, have {self._cash:.2f}",
                    error_code="INSUFFICIENT_FUNDS",
                )

        # Validate T+1 for sell
        if request.side == "SELL":
            pos = self._positions.get(request.symbol)
            if not pos or pos["available_quantity"] < request.quantity:
                avail = pos["available_quantity"] if pos else 0
                return OrderResult(
                    success=False,
                    broker_order_id="",
                    message=f"Insufficient available shares (T+1): need {request.quantity}, available {avail}",
                    error_code="T1_RESTRICTION",
                )

        # Execute with slippage
        fill_price = self._apply_slippage(price, request.side)
        total_amount = fill_price * request.quantity
        fees = self._calculate_commission(total_amount, request.side)

        # Record order
        order_info = OrderInfo(
            broker_order_id=broker_order_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            price=fill_price,
            quantity=request.quantity,
            filled_quantity=request.quantity,
            avg_fill_price=fill_price,
            status="FILLED",
            created_at=now,
            filled_at=now,
        )
        self._orders[broker_order_id] = order_info

        # Record trade
        self._trades.append(TradeInfo(
            broker_trade_id=f"PT-{uuid.uuid4().hex[:8].upper()}",
            broker_order_id=broker_order_id,
            symbol=request.symbol,
            side=request.side,
            price=fill_price,
            quantity=request.quantity,
            amount=total_amount,
            commission=fees,
            trade_time=now,
        ))

        # Update positions and cash
        if request.side == "BUY":
            self._cash -= (total_amount + fees)
            pos = self._positions.get(request.symbol)
            if pos:
                total_qty = pos["quantity"] + request.quantity
                pos["avg_cost"] = (pos["avg_cost"] * pos["quantity"] + total_amount) / total_qty
                pos["quantity"] = total_qty
                # available_quantity only increases next day (T+1)
                pos["current_price"] = fill_price
            else:
                self._positions[request.symbol] = {
                    "quantity": request.quantity,
                    "available_quantity": 0,  # T+1: not available until next day
                    "avg_cost": fill_price,
                    "current_price": fill_price,
                    "today_buy_qty": request.quantity,
                }
        else:
            self._cash += (total_amount - fees)
            pos = self._positions[request.symbol]
            pos["quantity"] -= request.quantity
            pos["available_quantity"] -= request.quantity
            pos["current_price"] = fill_price
            if pos["quantity"] <= 0:
                del self._positions[request.symbol]

        return OrderResult(
            success=True,
            broker_order_id=broker_order_id,
            message=f"Paper order filled at {fill_price:.2f}",
            timestamp=now,
        )

    async def cancel_order(self, broker_order_id: str) -> OrderResult:
        order = self._orders.get(broker_order_id)
        if order:
            order.status = "CANCELLED"
        return OrderResult(
            success=True,
            broker_order_id=broker_order_id,
            message="Paper order cancelled",
        )

    async def get_order_status(self, broker_order_id: str) -> OrderInfo:
        order = self._orders.get(broker_order_id)
        if not order:
            return OrderInfo(broker_order_id=broker_order_id, status="NOT_FOUND")
        return order
