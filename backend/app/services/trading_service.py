"""
Trading service – the central orchestrator for all order operations.

Flow: OrderCreate → RiskCheck → TradeProposal → [HumanConfirm] → Broker → Order → Trade

The AI NEVER bypasses this service for trading operations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.broker.base import BrokerAdapter, OrderRequest
from app.core.exceptions import (
    DuplicateOrderError,
    KillSwitchActiveError,
    LiveTradingDisabledError,
    RiskCheckFailedError,
)
from app.core.logging import get_trade_logger
from app.audit.logger import AuditLogger
from app.risk.engine import RiskEngine
from app.schemas.trading import OrderCreate, OrderResponse, TradeProposal

logger = get_trade_logger()


class TradingService:
    """
    Central trading service.

    Every order must pass through:
    1. Parameter validation
    2. Risk engine check
    3. (LIVE) Human confirmation
    4. Broker execution
    5. Audit logging
    """

    def __init__(self, broker: BrokerAdapter, risk_engine: RiskEngine):
        self.broker = broker
        self.risk_engine = risk_engine
        self._client_order_ids: set = set()

    def _generate_client_order_id(self) -> str:
        now = datetime.now(timezone.utc).strftime("%Y%m%d")
        seq = len(self._client_order_ids) + 1
        return f"ORDER-{now}-{seq:06d}"

    async def create_order(
        self,
        request: OrderCreate,
        account_id: str,
        is_live: bool = False,
    ) -> dict:
        """
        Create and validate an order.

        Steps:
        1. Generate client_order_id (idempotency)
        2. Validate parameters
        3. Run risk check
        4. If LIVE: require confirmation
        5. Submit to broker
        6. Audit log
        """
        client_order_id = self._generate_client_order_id()

        # Duplicate check
        if client_order_id in self._client_order_ids:
            raise DuplicateOrderError(client_order_id)

        # Risk check
        account = await self.broker.get_account()
        order_amount = (request.price or 0) * request.quantity
        risk_result = await self.risk_engine.check_order(
            symbol=request.symbol,
            side=request.side,
            price=request.price or 0,
            quantity=request.quantity,
            order_amount=order_amount,
            account_cash=account.available_cash,
            total_asset=account.total_asset,
            current_positions={},
            is_live=is_live,
        )

        AuditLogger.log_risk_check(
            symbol=request.symbol,
            side=request.side,
            passed=risk_result.passed,
            checks=risk_result.checks,
            rejections=risk_result.rejection_reasons,
        )

        if not risk_result.passed:
            logger.warning("Order rejected by risk engine",
                         symbol=request.symbol,
                         reasons=risk_result.rejection_reasons)
            return {
                "status": "RISK_REJECTED",
                "client_order_id": client_order_id,
                "rejection_reasons": risk_result.rejection_reasons,
                "risk_checks": risk_result.checks,
            }

        # LIVE: require human confirmation
        if is_live:
            AuditLogger.log_trade_proposal(
                symbol=request.symbol,
                direction=request.side,
                price=request.price or 0,
                quantity=request.quantity,
                strategy=request.strategy_name or "unknown",
            )
            return {
                "status": "PENDING_CONFIRM",
                "client_order_id": client_order_id,
                "proposal": {
                    "symbol": request.symbol,
                    "side": request.side,
                    "price": request.price,
                    "quantity": request.quantity,
                    "amount": order_amount,
                    "stop_loss": request.stop_loss_price,
                    "take_profit": request.take_profit_price,
                    "strategy": request.strategy_name,
                },
                "risk_checks": risk_result.checks,
            }

        # Execute via broker
        broker_request = OrderRequest(
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            price=request.price,
            quantity=request.quantity,
            client_order_id=client_order_id,
            strategy_name=request.strategy_name,
        )
        result = await self.broker.place_order(broker_request)

        self._client_order_ids.add(client_order_id)

        AuditLogger.log_order(
            order_id=client_order_id,
            symbol=request.symbol,
            side=request.side,
            status="FILLED" if result.success else "FAILED",
            broker=self.broker.name,
        )

        logger.info("Order executed",
                   symbol=request.symbol,
                   side=request.side,
                   quantity=request.quantity,
                   success=result.success)

        return {
            "status": "FILLED" if result.success else "FAILED",
            "client_order_id": client_order_id,
            "broker_order_id": result.broker_order_id,
            "message": result.message,
        }
