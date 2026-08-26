"""
Trading calendar for A-share market.

Must NOT use datetime.now() directly for trading decisions.
All time-dependent logic goes through this module.
"""
from __future__ import annotations

from datetime import datetime, time, timezone, timedelta
from typing import Optional

import pytz

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
