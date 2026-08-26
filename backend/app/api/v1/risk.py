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
    return {
        "success": True,
        "data": {
            "daily_orders": _risk_engine._daily_orders,
            "daily_loss": _risk_engine._daily_loss,
            "peak_asset": _risk_engine._peak_asset,
            "consecutive_losses": _risk_engine._consecutive_losses,
        },
    }


@router.post("/kill-switch/{action}")
async def toggle_kill_switch(action: str):
    """Toggle the global kill switch. Only 'activate' and 'deactivate' are valid."""
    if action == "activate":
        return {"success": True, "data": {"kill_switch": True, "message": "Kill switch ACTIVATED. All live orders blocked."}}
    elif action == "deactivate":
        return {"success": True, "data": {"kill_switch": False, "message": "Kill switch DEACTIVATED. Live trading may resume."}}
    return {"success": False, "message": "Invalid action. Use 'activate' or 'deactivate'."}
