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


class LLMMode(str, Enum):
    MOCK = "mock"
    MIMO = "mimo"


class MarketDataMode(str, Enum):
    MOCK = "mock"
    REAL = "real"


class MarketDataProviderName(str, Enum):
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    EASTMONEY = "eastmoney"


class RAGMode(str, Enum):
    MOCK = "mock"
    REAL = "real"


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
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/astock_ai"

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── MiMo AI ──────────────────────────────────────────────
    mimo_api_key: str = ""
    mimo_base_url: str = "https://api.mimo.com/v1"
    mimo_model: str = "mimo-v2.5-pro"
    llm_mode: LLMMode = LLMMode.MOCK
    market_data_mode: MarketDataMode = MarketDataMode.MOCK

    # ── Market Data ──────────────────────────────────────────
    market_data_provider: MarketDataProviderName = MarketDataProviderName.TUSHARE
    market_data_api_key: str = ""
    market_data_fallback_enabled: bool = True

    # ── Embedding / RAG ──────────────────────────────────────
    rag_mode: RAGMode = RAGMode.MOCK
    embedding_provider: str = "openai"          # openai | mock
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    embedding_base_url: str = ""                # defaults to mimo_base_url if empty
    embedding_api_key: str = ""                 # defaults to mimo_api_key if empty

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

    # ── Scheduler ────────────────────────────────────────────
    scheduler_enabled: bool = False  # Enable background data sync scheduler
    scheduler_stock_list_interval: int = 86400   # 24h in seconds
    scheduler_kline_interval: int = 3600         # 1h in seconds
    scheduler_kline_batch_size: int = 50          # Max symbols per kline sync batch

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
