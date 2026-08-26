"""
Trading calendar for A-share market.

Must NOT use datetime.now() directly for trading decisions.
All time-dependent logic goes through this module.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, date, time, timezone, timedelta
from typing import Optional

import pytz
from app.core.logging import get_logger

logger = get_logger("trading_calendar")

SHANGHAI_TZ = pytz.timezone("Asia/Shanghai")

# A-share trading sessions
MORNING_OPEN = time(9, 30)
MORNING_CLOSE = time(11, 30)
AFTERNOON_OPEN = time(13, 0)
AFTERNOON_CLOSE = time(15, 0)
PRE_MARKET_START = time(9, 15)
PRE_MARKET_END = time(9, 25)


class TradingCalendar:
    """Deterministic trading calendar for A-share market."""

    @staticmethod
    def now_shanghai() -> datetime:
        """Get current time in Shanghai timezone."""
        return datetime.now(SHANGHAI_TZ)

    @staticmethod
    def is_weekday(dt: Optional[datetime] = None) -> bool:
        dt = dt or TradingCalendar.now_shanghai()
        return dt.weekday() < 5  # Mon-Fri

    @staticmethod
    def is_trading_hours(dt: Optional[datetime] = None) -> bool:
        """Check if within A-share trading hours (9:30-11:30, 13:00-15:00)."""
        dt = dt or TradingCalendar.now_shanghai()
        t = dt.time()
        morning = MORNING_OPEN <= t <= MORNING_CLOSE
        afternoon = AFTERNOON_OPEN <= t <= AFTERNOON_CLOSE
        return morning or afternoon

    @staticmethod
    def is_pre_market(dt: Optional[datetime] = None) -> bool:
        dt = dt or TradingCalendar.now_shanghai()
        return PRE_MARKET_START <= dt.time() <= PRE_MARKET_END

    @staticmethod
    def market_phase(dt: Optional[datetime] = None) -> str:
        """Return current market phase: PRE_MARKET, MORNING, LUNCH, AFTERNOON, CLOSED."""
        dt = dt or TradingCalendar.now_shanghai()
        t = dt.time()
        if not TradingCalendar.is_weekday(dt):
            return "CLOSED"
        if t < PRE_MARKET_START:
            return "PRE_OPEN"
        if PRE_MARKET_START <= t <= PRE_MARKET_END:
            return "PRE_MARKET"
        if MORNING_OPEN <= t < MORNING_CLOSE:
            return "MORNING"
        if MORNING_CLOSE <= t < AFTERNOON_OPEN:
            return "LUNCH_BREAK"
        if AFTERNOON_OPEN <= t < AFTERNOON_CLOSE:
            return "AFTERNOON"
        return "CLOSED"

    @staticmethod
    def is_limit_up(price: float, pre_close: float, board: str = "MAIN") -> bool:
        """Check if a stock is at its daily price limit."""
        if pre_close <= 0:
            return False
        limit_pct = 0.20 if board in ("GEM", "STAR") else 0.10
        return (price - pre_close) / pre_close >= limit_pct - 0.001

    @staticmethod
    def is_limit_down(price: float, pre_close: float, board: str = "MAIN") -> bool:
        if pre_close <= 0:
            return False
        limit_pct = 0.20 if board in ("GEM", "STAR") else 0.10
        return (pre_close - price) / pre_close >= limit_pct - 0.001


class TradingCalendarProvider(ABC):
    """Interface for trading calendar data sources.

    Implementations can use:
    - AkShare (exchange calendar API)
    - Static holiday lists
    - Database-stored calendar
    - External API
    """

    @abstractmethod
    async def is_trading_day(self, d: date) -> bool:
        """Check if a specific date is an A-share trading day."""
        ...

    @abstractmethod
    async def get_trading_days(self, start: date, end: date) -> list[date]:
        """Get list of trading days in a date range."""
        ...


class WeekendFallbackCalendar(TradingCalendarProvider):
    """Fallback calendar that only checks weekends (no holiday awareness).

    Used when no external calendar data source is available.
    WARNING: Does NOT account for Chinese public holidays or make-up workdays.
    """

    async def is_trading_day(self, d: date) -> bool:
        return d.weekday() < 5  # Mon-Fri

    async def get_trading_days(self, start: date, end: date) -> list[date]:
        days = []
        current = start
        while current <= end:
            if current.weekday() < 5:
                days.append(current)
            current += timedelta(days=1)
        return days


class EnhancedTradingCalendar:
    """Trading calendar with pluggable provider.

    Falls back to WeekendFallbackCalendar if no provider is set.
    """

    _provider: Optional[TradingCalendarProvider] = None

    @classmethod
    def set_provider(cls, provider: TradingCalendarProvider) -> None:
        cls._provider = provider
        logger.info("trading_calendar_provider_set", provider=type(provider).__name__)

    @classmethod
    def get_provider(cls) -> TradingCalendarProvider:
        if cls._provider is None:
            cls._provider = WeekendFallbackCalendar()
        return cls._provider

    @classmethod
    async def is_trading_day(cls, d: Optional[date] = None) -> bool:
        d = d or TradingCalendar.now_shanghai().date()
        return await cls.get_provider().is_trading_day(d)

    @classmethod
    async def is_today_trading_day(cls) -> bool:
        today = TradingCalendar.now_shanghai().date()
        return await cls.is_trading_day(today)

    @classmethod
    async def should_run_sync(cls) -> bool:
        """Check if sync should run: trading day + within reasonable hours."""
        now = TradingCalendar.now_shanghai()
        if not await cls.is_trading_day(now.date()):
            return False
        # Allow sync from 9:00 to 18:00 Shanghai time
        return time(9, 0) <= now.time() <= time(18, 0)
