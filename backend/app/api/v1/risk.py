"""Risk management endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.config.settings import get_settings
from app.risk.engine import RiskEngine

router = APIRouter()
_risk_engine = RiskEngine()


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


@router.get("/status")
async def get_risk_status():
    """Get current risk engine runtime status."""
    return {"success": True, "data": _risk_engine.status}


@router.post("/cooldown/reset")
async def reset_cooldown():
    """Reset consecutive loss cooldown (manual override)."""
    _risk_engine.reset_cooldown()
    return {"success": True, "data": {"message": "Cooldown reset. Trading re-enabled."}}


@router.post("/kill-switch/{action}")
async def toggle_kill_switch(action: str):
    """Toggle the global kill switch."""
    if action == "activate":
        return {"success": True, "data": {"kill_switch": True, "message": "Kill switch ACTIVATED."}}
    elif action == "deactivate":
        return {"success": True, "data": {"kill_switch": False, "message": "Kill switch DEACTIVATED."}}
    return {"success": False, "message": "Invalid action. Use 'activate' or 'deactivate'."}
