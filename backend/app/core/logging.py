"""Structured logging using structlog."""
from __future__ import annotations

import logging
import sys

import structlog

from app.config.settings import get_settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer() if settings.app_debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a named structured logger."""
    return structlog.get_logger(name)


# ── Specialized loggers for different domains ────────────────────────────────
def get_trade_logger() -> structlog.BoundLogger:
    return structlog.get_logger("trade")

def get_risk_logger() -> structlog.BoundLogger:
    return structlog.get_logger("risk")

def get_ai_logger() -> structlog.BoundLogger:
    return structlog.get_logger("ai")

def get_data_logger() -> structlog.BoundLogger:
    return structlog.get_logger("data")

def get_audit_logger() -> structlog.BoundLogger:
    return structlog.get_logger("audit")
