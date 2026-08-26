"""Market data provider layer – abstracts data source differences."""
from app.market.base import (
    MarketDataProvider,
    QuoteData,
    KlineData,
    FinancialData,
    StockBasicInfo,
    MarketIndex,
    MarketSnapshot,
    DataSourceStatus,
    DataAvailability,
    DataFreshness,
    TechnicalIndicators,
    StockAnalysisSnapshot,
    Recommendation,
    MarketPhase,
)
from app.market.provider_manager import ProviderManager
from app.market.cache import MarketDataCache

__all__ = [
    "MarketDataProvider",
    "QuoteData",
    "KlineData",
    "FinancialData",
    "StockBasicInfo",
    "MarketIndex",
    "MarketSnapshot",
    "DataSourceStatus",
    "DataAvailability",
    "DataFreshness",
    "TechnicalIndicators",
    "StockAnalysisSnapshot",
    "Recommendation",
    "MarketPhase",
    "ProviderManager",
    "MarketDataCache",
]
