"""Trading endpoints – paper and live order management."""
from __future__ import annotations

from fastapi import APIRouter

from app.broker.mock_broker import MockBroker
from app.broker.paper_broker import PaperBroker
from app.risk.engine import RiskEngine
from app.schemas.trading import OrderCreate
from app.services.trading_service import TradingService

router = APIRouter()

# Default to paper broker for development
_broker = PaperBroker()
_risk_engine = RiskEngine()
_trading_service = TradingService(broker=_broker, risk_engine=_risk_engine)


@router.get("/account")
async def get_account():
    """Get trading account summary."""
    account = await _broker.get_account()
    return {
        "success": True,
        "data": {
            "account_id": account.account_id,
            "total_asset": account.total_asset,
            "cash": account.cash,
            "market_value": account.market_value,
            "available_cash": account.available_cash,
        },
    }


@router.get("/positions")
async def get_positions():
    """Get all open positions."""
    positions = await _broker.get_positions()
    return {"success": True, "data": [p.__dict__ for p in positions]}


@router.get("/orders")
async def get_orders(status: str = None):
    """Get orders, optionally filtered by status."""
    orders = await _broker.get_orders(status)
    return {"success": True, "data": [o.__dict__ for o in orders]}


@router.get("/trades")
async def get_trades(order_id: str = None):
    """Get trade fills."""
    trades = await _broker.get_trades(order_id)
    return {"success": True, "data": [t.__dict__ for t in trades]}


@router.post("/order")
async def place_order(order: OrderCreate):
    """
    Place a new order (paper or live depending on configuration).

    Flow: validate → risk check → [confirm if live] → execute → audit
    """
    result = await _trading_service.create_order(
        request=order,
        account_id="default",
        is_live=False,  # Always paper for now
    )
    return {"success": True, "data": result}


@router.post("/order/{order_id}/cancel")
async def cancel_order(order_id: str):
    """Cancel a pending order."""
    result = await _broker.cancel_order(order_id)
    return {
        "success": result.success,
        "data": {"broker_order_id": result.broker_order_id, "message": result.message},
    }


@router.get("/quote/{symbol}")
async def get_broker_quote(symbol: str):
    """Get quote via broker (may include account-specific data)."""
    quote = await _broker.get_quote(symbol)
    return {"success": True, "data": quote}
