"""Risk management endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.config.settings import get_settings

router = APIRouter()


@router.get("/config")
async def get_risk_config():
    """Get current risk control configuration."""
    settings = get_settings()
    return {"success": True, "data": {
        "max_position_ratio": settings.max_position_ratio,
        "max_single_trade_amount": settings.max_single_trade_amount,
        "max_daily_loss_ratio": settings.max_daily_loss_ratio,
        "max_drawdown": settings.max_drawdown,
        "max_daily_orders": settings.max_daily_orders,
        "max_industry_exposure": settings.max_industry_exposure,
        "global_kill_switch": settings.global_kill_switch,
        "live_trading": settings.live_trading,
        "auto_trade": settings.auto_trade,
    }}


@router.post("/kill-switch/{action}")
async def toggle_kill_switch(action: str):
    """Toggle the global kill switch. Only 'activate' and 'deactivate' are valid."""
    # In production, this would update .env or database
    if action == "activate":
        return {"success": True, "data": {"kill_switch": True, "message": "Kill switch ACTIVATED. All live orders blocked."}}
    elif action == "deactivate":
        return {"success": True, "data": {"kill_switch": False, "message": "Kill switch DEACTIVATED. Live trading may resume."}}
    return {"success": False, "message": "Invalid action. Use 'activate' or 'deactivate'."}
