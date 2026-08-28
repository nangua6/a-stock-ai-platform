"""
Enhanced market data base types.

Extends the original QuoteData/KlineData/FinancialData with richer types
for snapshots, data availability tracking, and AI context building.

All original types remain unchanged for backward compatibility.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enums ──────────────────────────────────────────────────────────────────────

class DataFreshness(str, Enum):
    """Freshness state of market data."""
    FRESH = "fresh"            # Within normal TTL
    STALE = "stale"            # Past TTL but still usable with caution
    UNAVAILABLE = "unavailable"  # No data at all


class Recommendation(str, Enum):
    """Structured recommendation for AI analysis output."""
    WATCH = "WATCH"
    BUY_CANDIDATE = "BUY_CANDIDATE"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    AVOID = "AVOID"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class MarketPhase(str, Enum):
    """A-share market phases."""
    PRE_OPEN = "PRE_OPEN"
    PRE_MARKET = "PRE_MARKET"
    MORNING = "MORNING"
    LUNCH_BREAK = "LUNCH_BREAK"
    AFTERNOON = "AFTERNOON"
    CLOSED = "CLOSED"


# ── Original data types (preserved for backward compatibility) ─────────────────

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
    report_period: str = ""          # e.g. "2025-12-31" or "2025Q4"
    published_at: Optional[str] = None   # disclosure date (when the report was published)
    retrieved_at: str = ""           # when this data was fetched
    data_source: str = ""
    data_quality: str = "UNKNOWN"    # GOOD | PARTIAL | UNAVAILABLE

    # Income statement
    revenue: Optional[float] = None            # total revenue (yuan)
    revenue_yoy: Optional[float] = None        # revenue YoY growth %
    net_profit: Optional[float] = None         # net profit (yuan)
    net_profit_yoy: Optional[float] = None     # net profit YoY growth %
    gross_margin: Optional[float] = None       # gross profit margin %
    net_margin: Optional[float] = None         # net profit margin %

    # Balance sheet / returns
    roe: Optional[float] = None                # return on equity %
    roa: Optional[float] = None                # return on assets %
    eps: Optional[float] = None                # earnings per share (yuan)

    # Cash flow
    operating_cash_flow: Optional[float] = None  # operating cash flow per share (yuan)

    # Valuation
    pe_ratio: Optional[float] = None           # P/E ratio (dynamic)
    pb_ratio: Optional[float] = None           # P/B ratio
    market_cap: Optional[float] = None         # total market cap (yuan)
    total_share: Optional[float] = None        # total shares outstanding


# ── New enhanced types ─────────────────────────────────────────────────────────

@dataclass
class NewsItem:
    """A single news article with full provenance."""
    id: str = ""                        # unique news id
    title: str = ""
    summary: str = ""                   # original or generated summary
    content: str = ""                   # full content if available
    published_at: Optional[str] = None  # when the article was published (from source)
    retrieved_at: str = ""              # when we fetched it
    source: str = ""                    # e.g. "证券时报网", "界面新闻"
    url: str = ""
    symbols: List[str] = field(default_factory=list)  # normalized: ["600519.SH"]
    citation_id: str = ""              # e.g. "news_600519_20260827_001"
    data_quality: str = "UNKNOWN"      # GOOD | PARTIAL | UNAVAILABLE
    content_hash: str = ""             # for dedup


@dataclass
class AnnouncementItem:
    """A single company announcement with full provenance."""
    id: str = ""                            # unique announcement id
    symbol: str = ""                        # normalized: "600519.SH"
    name: str = ""                          # stock name: "贵州茅台"
    title: str = ""                         # announcement title
    summary: str = ""                       # brief summary
    content: str = ""                       # full content if available
    announcement_type: str = "OTHER"        # ANNUAL_REPORT / QUARTERLY_REPORT / ...
    published_at: Optional[str] = None      # when the announcement was published (from source)
    retrieved_at: str = ""                  # when we fetched it
    source: str = ""                        # e.g. "东方财富"
    url: str = ""                           # announcement URL
    citation_id: str = ""                   # e.g. "announcement_600519_SH_20260815_001"
    data_quality: str = "UNKNOWN"           # GOOD | PARTIAL | UNAVAILABLE
    content_hash: str = ""                  # for dedup


@dataclass
class StockBasicInfo:
    """Basic stock metadata."""
    symbol: str = ""
    name: str = ""
    market: str = ""          # SH | SZ | BJ
    board: str = ""           # MAIN | GEM | STAR | BSE
    industry: str = ""
    industry_code: str = ""
    area: str = ""
    list_date: str = ""
    is_st: bool = False
    is_suspended: bool = False
    is_active: bool = True
    data_source: str = ""


@dataclass
class MarketIndex:
    """A single market index data point."""
    name: str = ""            # e.g. 上证指数
    code: str = ""            # e.g. sh000001
    price: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    amount: float = 0.0
    timestamp: str = ""


@dataclass
class MarketSnapshot:
    """Full market overview snapshot."""
    indices: List[MarketIndex] = field(default_factory=list)
    up_count: int = 0
    down_count: int = 0
    flat_count: int = 0
    limit_up_count: int = 0
    limit_down_count: int = 0
    total_amount: float = 0.0       # 总成交额 (元)
    northbound_flow: float = 0.0    # 北向资金净流入 (元)
    market_phase: str = ""
    timestamp: str = ""
    data_source: str = ""


@dataclass
class DataAvailability:
    """Tracks data quality and freshness for a specific data request."""
    is_available: bool = True
    freshness: DataFreshness = DataFreshness.FRESH
    provider: str = ""
    data_timestamp: str = ""        # When the data was produced
    fetched_at: str = ""            # When we fetched it
    data_age_seconds: float = 0.0   # How old the data is
    error_message: str = ""
    error_type: str = ""

    @property
    def is_usable(self) -> bool:
        """Data is usable if available and not stale beyond acceptable limits."""
        return self.is_available and self.freshness != DataFreshness.UNAVAILABLE

    @property
    def requires_disclaimer(self) -> bool:
        """If True, AI must note that data may be outdated."""
        return self.freshness == DataFreshness.STALE

    def to_dict(self) -> dict:
        return {
            "is_available": self.is_available,
            "freshness": self.freshness.value,
            "provider": self.provider,
            "data_timestamp": self.data_timestamp,
            "fetched_at": self.fetched_at,
            "data_age_seconds": round(self.data_age_seconds, 1),
            "error_message": self.error_message,
            "error_type": self.error_type,
        }


@dataclass
class DataSourceStatus:
    """Health status of a market data provider."""
    provider: str = ""
    is_healthy: bool = True
    last_success: str = ""
    last_failure: str = ""
    consecutive_failures: int = 0
    last_error: str = ""
    total_requests: int = 0
    total_failures: int = 0

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_failures / self.total_requests

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "is_healthy": self.is_healthy,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "consecutive_failures": self.consecutive_failures,
            "failure_rate": round(self.failure_rate, 4),
            "total_requests": self.total_requests,
        }


@dataclass
class TechnicalIndicators:
    """Computed technical indicators for a stock."""
    symbol: str = ""
    # Moving averages
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    ema12: float = 0.0
    ema26: float = 0.0
    # MACD
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    # RSI
    rsi: float = 0.0
    # KDJ
    kdj_k: float = 0.0
    kdj_d: float = 0.0
    kdj_j: float = 0.0
    # Bollinger Bands
    boll_upper: float = 0.0
    boll_middle: float = 0.0
    boll_lower: float = 0.0
    # ATR
    atr: float = 0.0
    # Volume
    volume_ma5: float = 0.0
    volume_ma10: float = 0.0
    volume_ma20: float = 0.0
    # Derived
    volatility: float = 0.0     # Annualized volatility
    turnover_rate: float = 0.0  # 换手率
    amplitude: float = 0.0      # 振幅
    computed_at: str = ""
    period: int = 0             # Number of bars used

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class StockAnalysisSnapshot:
    """
    Unified snapshot for AI analysis.

    Combines basic info, quote, klines, technicals, risk, and data quality
    into a single structured object for AI Agent consumption.
    """
    # Identity
    symbol: str = ""
    name: str = ""
    industry: str = ""
    market: str = ""

    # Quote
    current_price: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    amount: float = 0.0
    turnover: float = 0.0
    pre_close: float = 0.0

    # K-line (recent bars)
    klines: List[KlineData] = field(default_factory=list)

    # Technical indicators
    technicals: Optional[TechnicalIndicators] = None

    # Financials
    financials: Optional[FinancialData] = None

    # Risk
    volatility: float = 0.0
    max_drawdown: float = 0.0

    # Data quality
    data_quality: DataAvailability = field(default_factory=DataAvailability)
    data_source: str = ""
    snapshot_time: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "industry": self.industry,
            "market": self.market,
            "current_price": self.current_price,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "amount": self.amount,
            "turnover": self.turnover,
            "pre_close": self.pre_close,
            "kline_count": len(self.klines),
            "technicals": self.technicals.to_dict() if self.technicals else None,
            "financials": self.financials.__dict__ if self.financials else None,
            "volatility": self.volatility,
            "max_drawdown": self.max_drawdown,
            "data_quality": self.data_quality.to_dict(),
            "data_source": self.data_source,
            "snapshot_time": self.snapshot_time,
        }


# ── Abstract Provider Interface (preserved) ────────────────────────────────────

class MarketDataProvider(ABC):
    """
    Abstract market data provider.

    Implementations: AkShareProvider, MockMarketDataProvider, etc.
    The system uses a ProviderManager with fallback chain.
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
