"""Domain exceptions for the trading platform."""
from __future__ import annotations


class AppError(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            code="NOT_FOUND",
            status_code=404,
        )


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=400)


class TradingError(AppError):
    """Base for all trading-related errors."""
    pass


class KillSwitchActiveError(TradingError):
    def __init__(self):
        super().__init__(
            message="GLOBAL KILL SWITCH is active. All live orders are blocked.",
            code="KILL_SWITCH_ACTIVE",
            status_code=403,
        )


class LiveTradingDisabledError(TradingError):
    def __init__(self):
        super().__init__(
            message="Live trading is disabled. Enable LIVE_TRADING=true.",
            code="LIVE_TRADING_DISABLED",
            status_code=403,
        )


class RiskCheckFailedError(TradingError):
    def __init__(self, details: str):
        super().__init__(
            message=f"Risk check failed: {details}",
            code="RISK_CHECK_FAILED",
            status_code=403,
        )


class InsufficientFundsError(TradingError):
    def __init__(self, required: float, available: float):
        super().__init__(
            message=f"Insufficient funds: required {required:.2f}, available {available:.2f}",
            code="INSUFFICIENT_FUNDS",
            status_code=400,
        )


class DuplicateOrderError(TradingError):
    def __init__(self, client_order_id: str):
        super().__init__(
            message=f"Duplicate order detected: {client_order_id}",
            code="DUPLICATE_ORDER",
            status_code=409,
        )


class MarketClosedError(TradingError):
    def __init__(self):
        super().__init__(
            message="Market is currently closed.",
            code="MARKET_CLOSED",
            status_code=400,
        )


class BrokerError(TradingError):
    def __init__(self, message: str):
        super().__init__(message=message, code="BROKER_ERROR", status_code=502)


class DataSourceError(AppError):
    def __init__(self, provider: str, message: str):
        super().__init__(
            message=f"Data source error ({provider}): {message}",
            code="DATA_SOURCE_ERROR",
            status_code=502,
        )


class AIAgentError(AppError):
    def __init__(self, agent_name: str, message: str):
        super().__init__(
            message=f"AI Agent [{agent_name}] error: {message}",
            code="AI_AGENT_ERROR",
            status_code=500,
        )
