"""Application settings using pydantic-settings."""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class BrokerProvider(str, Enum):
    MOCK = "mock"
    PAPER = "paper"
    QMT = "qmt"
    PTRADE = "ptrade"


class MarketDataProviderName(str, Enum):
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    EASTMONEY = "eastmoney"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/astock_ai"

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── MiMo AI ──────────────────────────────────────────────
    mimo_api_key: str = ""
    mimo_base_url: str = "https://api.mimo.com/v1"
    mimo_model: str = "mimo-v2.5-pro"

    # ── Market Data ──────────────────────────────────────────
    market_data_provider: MarketDataProviderName = MarketDataProviderName.TUSHARE
    market_data_api_key: str = ""
    market_data_fallback_enabled: bool = True

    # ── Broker ───────────────────────────────────────────────
    broker_provider: BrokerProvider = BrokerProvider.MOCK
    broker_api_url: str = ""
    broker_account_id: str = ""
    broker_api_key: str = ""
    broker_api_secret: str = ""

    # ── Trading Safety Defaults ──────────────────────────────
    paper_trading: bool = True
    live_trading: bool = False
    auto_trade: bool = False
    global_kill_switch: bool = True
    live_order_require_confirmation: bool = True

    # ── Risk Control Defaults ────────────────────────────────
    max_position_ratio: float = Field(default=0.20, description="最大单股仓位比例")
    max_single_trade_amount: float = Field(default=100000, description="单笔最大交易金额")
    max_daily_loss_ratio: float = Field(default=0.03, description="单日最大亏损比例")
    max_drawdown: float = Field(default=0.10, description="最大回撤比例")
    max_daily_orders: int = Field(default=20, description="单日最大订单数")
    max_industry_exposure: float = Field(default=0.40, description="最大行业暴露")

    @property
    def is_live_trading_allowed(self) -> bool:
        """Check if live trading is allowed based on all safety checks."""
        return (
            self.live_trading
            and not self.global_kill_switch
            and self.broker_provider != BrokerProvider.MOCK
        )

    @property
    def effective_broker(self) -> BrokerProvider:
        """Return the effective broker, falling back to paper in non-live mode."""
        if self.live_trading and not self.global_kill_switch:
            return self.broker_provider
        return BrokerProvider.PAPER if self.paper_trading else BrokerProvider.MOCK


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
