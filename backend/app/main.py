"""
A股智能投研平台 – FastAPI Application.

This is the main entry point for the backend API server.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import AppError
from app.core.logging import setup_logging, get_logger
from app.market.provider_manager import ProviderManager
from app.market.mock_provider import MockMarketDataProvider
from app.services.scheduler import Scheduler

_scheduler: Scheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    global _scheduler
    settings = get_settings()
    setup_logging()
    logger = get_logger("main")
    logger.info("Starting A-Stock AI Platform", env=settings.app_env.value)

    # Initialize database tables (dev convenience)
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning("Database init failed (may need to start PostgreSQL)", error=str(e))

    # Start scheduler if enabled
    if settings.scheduler_enabled:
        try:
            _scheduler = Scheduler()
            _setup_scheduler_jobs(_scheduler, settings)
            await _scheduler.start()
            logger.info("Scheduler started", job_count=len(_scheduler._jobs))
        except Exception as e:
            logger.warning("Scheduler start failed", error=str(e))
            _scheduler = None

    yield

    # Shutdown
    if _scheduler is not None:
        try:
            await _scheduler.stop()
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.warning("Scheduler stop failed", error=str(e))

    await close_db()
    logger.info("Shutdown complete")


def _setup_scheduler_jobs(scheduler: Scheduler, settings) -> None:
    """Register default sync jobs with the scheduler."""
    from app.core.database import get_db_context
    from app.services.sync_service import SyncService
    from app.services.trading_calendar import EnhancedTradingCalendar

    provider = ProviderManager(providers=[MockMarketDataProvider()])

    async def sync_stock_list_job():
        """Sync stock list from provider. Runs daily."""
        if not await EnhancedTradingCalendar.should_run_sync():
            return {"skipped": "not_weekday"}
        async with get_db_context() as session:
            svc = SyncService(session, provider)
            return await svc.sync_stock_list()

    async def sync_klines_job():
        """Sync klines for active stocks. Runs hourly during trading days."""
        if not await EnhancedTradingCalendar.should_run_sync():
            return {"skipped": "not_weekday"}
        async with get_db_context() as session:
            from app.repositories.factory import RepositoryFactory
            repos = RepositoryFactory(session)
            stocks = await repos.stocks.get_active_stocks()
            if not stocks:
                return {"skipped": "no_stocks_in_db"}
            symbols = [s.symbol for s in stocks[:settings.scheduler_kline_batch_size]]
            svc = SyncService(session, provider)
            return await svc.sync_klines(symbols)

    async def sync_technical_job():
        """Compute technical snapshots after klines are synced."""
        if not await EnhancedTradingCalendar.should_run_sync():
            return {"skipped": "not_weekday"}
        async with get_db_context() as session:
            from app.repositories.factory import RepositoryFactory
            repos = RepositoryFactory(session)
            stocks = await repos.stocks.get_active_stocks()
            if not stocks:
                return {"skipped": "no_stocks_in_db"}
            symbols = [s.symbol for s in stocks[:settings.scheduler_kline_batch_size]]
            svc = SyncService(session, provider)
            return await svc.compute_technical_snapshots(symbols)

    scheduler.add_job(
        name="stock_list_sync",
        func=sync_stock_list_job,
        interval_seconds=settings.scheduler_stock_list_interval,
    )
    scheduler.add_job(
        name="kline_sync",
        func=sync_klines_job,
        interval_seconds=settings.scheduler_kline_interval,
    )
    scheduler.add_job(
        name="technical_snapshot",
        func=sync_technical_job,
        interval_seconds=settings.scheduler_kline_interval + 300,  # 5 min after kline sync
    )

def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title="A股智能投研与自动化交易系统",
        description="A-share intelligent investment research and automated trading platform powered by MiMo AI",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "code": exc.status_code,
                "message": exc.message,
                "error_code": exc.code,
            },
        )

    # Register API routes
    from app.api.v1 import health, market, trading, analysis, portfolio, risk, backtest, data
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(market.router, prefix="/api/v1/market", tags=["Market Data"])
    app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])
    app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["AI Analysis"])
    app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
    app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk"])
    app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["Backtest"])
    app.include_router(data.router, prefix="/api/v1/data", tags=["Data Management"])

    return app


app = create_app()
