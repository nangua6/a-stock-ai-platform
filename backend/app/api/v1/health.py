"""Health check and system status endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config.settings import get_settings
from app.services.trading_calendar import TradingCalendar

router = APIRouter()


@router.get("/health")
async def health_check():
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "env": settings.app_env.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
async def system_status():
    settings = get_settings()
    return {
        "trading_mode": "LIVE" if settings.live_trading else ("PAPER" if settings.paper_trading else "RESEARCH"),
        "kill_switch": settings.global_kill_switch,
        "auto_trade": settings.auto_trade,
        "market_phase": TradingCalendar.market_phase(),
        "market_data_provider": settings.market_data_provider.value,
        "broker_provider": settings.effective_broker.value,
        "risk_params": {
            "max_position_ratio": settings.max_position_ratio,
            "max_single_trade_amount": settings.max_single_trade_amount,
            "max_daily_loss_ratio": settings.max_daily_loss_ratio,
            "max_drawdown": settings.max_drawdown,
            "max_daily_orders": settings.max_daily_orders,
        },
    }
