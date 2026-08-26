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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
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

    yield

    # Shutdown
    await close_db()
    logger.info("Shutdown complete")


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
