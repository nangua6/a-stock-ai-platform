"""
Technical Analysis Service – standalone indicator computation.

All indicators operate on standardized KlineData lists.
No network calls, no LLM, no external dependencies.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from app.market.base import KlineData, TechnicalIndicators
from app.core.logging import get_logger

logger = get_logger("technical_analysis")


def _sma(values: List[float], period: int) -> float:
    """Simple Moving Average of the last `period` values."""
    if len(values) < period:
        return 0.0
    return sum(values[-period:]) / period


def _ema(values: List[float], period: int) -> List[float]:
    """Exponential Moving Average – returns full series."""
    if not values:
        return []
    multiplier = 2 / (period + 1)
    result = [values[0]]
    for i in range(1, len(values)):
        result.append(values[i] * multiplier + result[-1] * (1 - multiplier))
    return result


def _rsi(closes: List[float], period: int = 14) -> float:
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return 0.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _macd(closes: List[float], fast: int = 12, slow: int = 26, signal_period: int = 9):
    """MACD: returns (macd_line, signal_line, histogram) as lists."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = _ema(macd_line, signal_period)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, histogram


def _kdj(highs: List[float], lows: List[float], closes: List[float],
         n: int = 9, m1: int = 3, m2: int = 3):
    """KDJ indicator."""
    if len(closes) < n:
        return 50.0, 50.0, 50.0

    k_values = [50.0]
    d_values = [50.0]

    for i in range(n - 1, len(closes)):
        window_high = max(highs[i - n + 1:i + 1])
        window_low = min(lows[i - n + 1:i + 1])
        if window_high == window_low:
            rsv = 50.0
        else:
            rsv = (closes[i] - window_low) / (window_high - window_low) * 100
        k = (m1 - 1) / m1 * k_values[-1] + 1 / m1 * rsv
        d = (m2 - 1) / m2 * d_values[-1] + 1 / m2 * k
        k_values.append(k)
        d_values.append(d)

    k = k_values[-1]
    d = d_values[-1]
    j = 3 * k - 2 * d
    return round(k, 2), round(d, 2), round(j, 2)


def _bollinger(closes: List[float], period: int = 20, num_std: float = 2.0):
    """Bollinger Bands: returns (upper, middle, lower)."""
    if len(closes) < period:
        return 0.0, 0.0, 0.0
    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = math.sqrt(variance)
    return round(middle + num_std * std, 2), round(middle, 2), round(middle - num_std * std, 2)


def _atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Average True Range."""
    if len(closes) < period + 1:
        return 0.0
    true_ranges = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)
    if len(true_ranges) < period:
        return 0.0
    return sum(true_ranges[-period:]) / period


def _volatility(closes: List[float], period: int = 20) -> float:
    """Annualized volatility from log returns."""
    if len(closes) < period + 1:
        return 0.0
    import math
    log_returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
    if len(log_returns) < period:
        return 0.0
    window = log_returns[-period:]
    mean = sum(window) / len(window)
    variance = sum((r - mean) ** 2 for r in window) / len(window)
    daily_vol = math.sqrt(variance)
    annual_vol = daily_vol * math.sqrt(242)  # A-share: ~242 trading days
    return round(annual_vol, 4)


class TechnicalAnalysisService:
    """
    Standalone technical indicator computation.

    Input: List[KlineData] (standardized OHLCV bars)
    Output: TechnicalIndicators dataclass

    No network, no LLM, no external dependencies.
    """

    MIN_BARS = 5
    RECOMMENDED_BARS = 60

    def compute(self, klines: List[KlineData]) -> TechnicalIndicators:
        """
        Compute all technical indicators from kline data.

        Handles insufficient data gracefully — missing indicators default to 0.
        """
        if not klines:
            return TechnicalIndicators()

        symbol = klines[0].symbol
        n = len(klines)

        closes = [k.close for k in klines]
        highs = [k.high for k in klines]
        lows = [k.low for k in klines]
        volumes = [float(k.volume) for k in klines]

        # Moving averages
        ma5 = round(_sma(closes, 5), 2) if n >= 5 else 0.0
        ma10 = round(_sma(closes, 10), 2) if n >= 10 else 0.0
        ma20 = round(_sma(closes, 20), 2) if n >= 20 else 0.0
        ma60 = round(_sma(closes, 60), 2) if n >= 60 else 0.0

        # EMA
        ema_series = _ema(closes, 12)
        ema12 = round(ema_series[-1], 2) if ema_series else 0.0
        ema_series_26 = _ema(closes, 26)
        ema26 = round(ema_series_26[-1], 2) if ema_series_26 else 0.0

        # MACD
        if n >= 35:
            macd_line, signal_line, histogram = _macd(closes)
            macd_val = round(macd_line[-1], 4)
            signal_val = round(signal_line[-1], 4)
            hist_val = round(histogram[-1], 4)
        else:
            macd_val = signal_val = hist_val = 0.0

        # RSI
        rsi_val = round(_rsi(closes, 14), 2) if n >= 15 else 0.0

        # KDJ
        if n >= 9:
            k_val, d_val, j_val = _kdj(highs, lows, closes)
        else:
            k_val = d_val = j_val = 0.0

        # Bollinger
        boll_upper, boll_middle, boll_lower = _bollinger(closes) if n >= 20 else (0.0, 0.0, 0.0)

        # ATR
        atr_val = round(_atr(highs, lows, closes, 14), 4) if n >= 15 else 0.0

        # Volume MAs
        vol_ma5 = round(_sma(volumes, 5), 0) if n >= 5 else 0.0
        vol_ma10 = round(_sma(volumes, 10), 0) if n >= 10 else 0.0
        vol_ma20 = round(_sma(volumes, 20), 0) if n >= 20 else 0.0

        # Volatility
        vol_val = _volatility(closes) if n >= 21 else 0.0

        # Turnover (from last kline)
        last_turnover = klines[-1].turnover if klines else 0.0

        # Amplitude (振幅) from last bar
        last = klines[-1]
        amplitude = round((last.high - last.low) / last.close * 100, 2) if last.close > 0 else 0.0

        return TechnicalIndicators(
            symbol=symbol,
            ma5=ma5,
            ma10=ma10,
            ma20=ma20,
            ma60=ma60,
            ema12=ema12,
            ema26=ema26,
            macd_line=macd_val,
            macd_signal=signal_val,
            macd_histogram=hist_val,
            rsi=rsi_val,
            kdj_k=k_val,
            kdj_d=d_val,
            kdj_j=j_val,
            boll_upper=boll_upper,
            boll_middle=boll_middle,
            boll_lower=boll_lower,
            atr=atr_val,
            volume_ma5=vol_ma5,
            volume_ma10=vol_ma10,
            volume_ma20=vol_ma20,
            volatility=vol_val,
            turnover_rate=last_turnover,
            amplitude=amplitude,
            computed_at=klines[-1].trade_date if klines else "",
            period=n,
        )
