"""
Audit logger – records every significant action for full traceability.

Trace chain: User → Agent → Tool → Strategy → Risk → Trade Proposal → Confirmation → Broker → Order → Trade
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.logging import get_audit_logger

logger = get_audit_logger()


class AuditLogger:
    """Structured audit logger for compliance and debugging."""

    @staticmethod
    def log_agent_run(
        agent_name: str,
        prompt: str,
        response: str,
        user_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ):
        logger.info(
            "agent_run",
            event_type="AGENT_RUN",
            agent=agent_name,
            prompt_len=len(prompt),
            response_len=len(response),
            user_id=user_id,
            duration_ms=duration_ms,
        )

    @staticmethod
    def log_tool_call(
        tool_name: str,
        arguments: dict,
        result: Any,
        agent_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        logger.info(
            "tool_call",
            event_type="TOOL_CALL",
            tool=tool_name,
            agent=agent_name,
            args=arguments,
            user_id=user_id,
        )

    @staticmethod
    def log_risk_check(
        symbol: str,
        side: str,
        passed: bool,
        checks: list,
        rejections: list,
        user_id: Optional[str] = None,
    ):
        logger.info(
            "risk_check",
            event_type="RISK_CHECK",
            symbol=symbol,
            side=side,
            passed=passed,
            checks=checks,
            rejections=rejections,
            user_id=user_id,
        )

    @staticmethod
    def log_trade_proposal(
        symbol: str,
        direction: str,
        price: float,
        quantity: int,
        strategy: str,
        user_id: Optional[str] = None,
    ):
        logger.info(
            "trade_proposal",
            event_type="TRADE_PROPOSAL",
            symbol=symbol,
            direction=direction,
            price=price,
            quantity=quantity,
            strategy=strategy,
            user_id=user_id,
        )

    @staticmethod
    def log_order(
        order_id: str,
        symbol: str,
        side: str,
        status: str,
        broker: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        logger.info(
            "order",
            event_type="ORDER",
            order_id=order_id,
            symbol=symbol,
            side=side,
            status=status,
            broker=broker,
            user_id=user_id,
        )

    @staticmethod
    def log_system_event(event_type: str, message: str, details: Optional[dict] = None):
        logger.warning(
            "system_event",
            event_type=event_type,
            message=message,
            details=details or {},
        )
