"""Data management endpoints – sync status, manual sync triggers, data health."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.market.provider_manager import ProviderManager
from app.market.mock_provider import MockMarketDataProvider
from app.market.cache import MarketDataCache

router = APIRouter()

_cache = MarketDataCache()
_provider = ProviderManager(
    providers=[MockMarketDataProvider()],
    cache=_cache,
)


# ── Request models ────────────────────────────────────────────────────────

class SyncKlineRequest(BaseModel):
    symbols: list[str]
    timeframe: str = "D"
    limit: int = 200


class SyncFullRequest(BaseModel):
    symbols: list[str]


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/status")
async def get_data_status():
    """Get overall data status: providers, cache, DB stats."""
    from app.core.database import get_db_context
    from app.services.market_data_service import MarketDataService

    async with get_db_context() as session:
        svc = MarketDataService(session, _provider)
        status = await svc.get_data_status()
    return {"success": True, "data": status}


@router.get("/sync/status")
async def get_sync_status():
    """Get current sync job status summary."""
    from app.core.database import get_db_context
    from app.services.sync_service import SyncService

    async with get_db_context() as session:
        svc = SyncService(session, _provider)
        status = await svc.get_sync_status()
    return {"success": True, "data": status}


@router.get("/sync/history")
async def get_sync_history(
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get sync job history."""
    from app.core.database import get_db_context
    from app.services.sync_service import SyncService

    async with get_db_context() as session:
        svc = SyncService(session, _provider)
        history = await svc.get_sync_history(job_type=job_type, limit=limit)
    return {"success": True, "data": history}


@router.post("/sync/stock-list")
async def run_sync_stock_list():
    """Trigger stock list sync."""
    from app.core.database import get_db_context
    from app.services.sync_service import SyncService

    async with get_db_context() as session:
        svc = SyncService(session, _provider)
        result = await svc.sync_stock_list()
    return {"success": True, "data": result}


@router.post("/sync/klines")
async def run_sync_klines(req: SyncKlineRequest):
    """Trigger kline sync for specified symbols."""
    from app.core.database import get_db_context
    from app.services.sync_service import SyncService

    async with get_db_context() as session:
        svc = SyncService(session, _provider)
        result = await svc.sync_klines(req.symbols, timeframe=req.timeframe, limit=req.limit)
    return {"success": True, "data": result}


@router.post("/sync/technical")
async def run_sync_technical(req: SyncKlineRequest):
    """Compute and persist technical snapshots for specified symbols."""
    from app.core.database import get_db_context
    from app.services.sync_service import SyncService

    async with get_db_context() as session:
        svc = SyncService(session, _provider)
        result = await svc.compute_technical_snapshots(req.symbols)
    return {"success": True, "data": result}


@router.post("/sync/analysis")
async def run_sync_analysis(req: SyncKlineRequest):
    """Compute and persist analysis snapshots for specified symbols."""
    from app.core.database import get_db_context
    from app.services.sync_service import SyncService

    async with get_db_context() as session:
        svc = SyncService(session, _provider)
        result = await svc.compute_analysis_snapshots(req.symbols)
    return {"success": True, "data": result}


@router.post("/sync/full")
async def run_sync_full(req: SyncFullRequest):
    """Run full pipeline: stock_list + klines + technical + analysis."""
    from app.core.database import get_db_context
    from app.services.sync_service import SyncService

    async with get_db_context() as session:
        svc = SyncService(session, _provider)
        result = await svc.sync_full(req.symbols)
    return {"success": True, "data": result}


@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status (if running)."""
    from app.main import _scheduler
    if _scheduler is not None:
        return {"success": True, "data": _scheduler.get_status()}
    return {
        "success": True,
        "data": {
            "running": False,
            "note": "Scheduler not enabled. Set SCHEDULER_ENABLED=true to start.",
        },
    }
