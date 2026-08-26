"""Abstract market data provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class QuoteData:
    symbol: str = ""
    name: str = ""
    price: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0
    volume: int = 0
    amount: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    bid1_price: float = 0.0
    ask1_price: float = 0.0
    bid1_volume: int = 0
    ask1_volume: int = 0
    timestamp: str = ""
    data_source: str = ""


@dataclass
class KlineData:
    symbol: str = ""
    trade_date: str = ""
    timeframe: str = "D"
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    amount: float = 0.0
    change_pct: float = 0.0
    turnover: float = 0.0
    data_source: str = ""
    available_time: str = ""


@dataclass
class FinancialData:
    symbol: str = ""
    report_date: str = ""
    revenue: float = 0.0
    net_profit: float = 0.0
    eps: float = 0.0
    roe: float = 0.0
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    market_cap: float = 0.0
    total_share: float = 0.0
    data_source: str = ""


class MarketDataProvider(ABC):
    """
    Abstract market data provider.

    Implementations: TushareProvider, AkshareProvider, EastMoneyProvider.
    The system uses a fallback chain if the primary provider fails.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        ...

    @abstractmethod
    async def get_realtime_quote(self, symbol: str) -> QuoteData:
        """Get real-time quote for a single stock."""
        ...

    @abstractmethod
    async def get_realtime_quotes(self, symbols: List[str]) -> List[QuoteData]:
        """Batch get real-time quotes."""
        ...

    @abstractmethod
    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "D",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[KlineData]:
        """Get K-line data (OHLCV bars)."""
        ...

    @abstractmethod
    async def get_financial_data(self, symbol: str) -> FinancialData:
        """Get fundamental financial data for a stock."""
        ...

    @abstractmethod
    async def get_stock_list(self, market: Optional[str] = None) -> List[dict]:
        """Get list of all stocks, optionally filtered by market."""
        ...

    @abstractmethod
    async def get_industry_stocks(self, industry_code: str) -> List[str]:
        """Get all stocks in an industry."""
        ...

    @abstractmethod
    async def get_market_overview(self) -> dict:
        """Get market overview (indices, breadth, sentiment)."""
        ...

    @abstractmethod
    async def get_money_flow(self, symbol: str) -> dict:
        """Get capital flow data."""
        ...

    @abstractmethod
    async def get_news(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        """Get recent news."""
        ...

    @abstractmethod
    async def get_announcements(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        """Get recent announcements."""
        ...
