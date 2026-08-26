"""Tests for TechnicalAnalysisService."""
import pytest
from app.services.technical_analysis import TechnicalAnalysisService
from app.market.base import KlineData


def _make_klines(closes, volumes=None, n=None):
    """Helper to create KlineData list from close prices."""
    n = n or len(closes)
    if volumes is None:
        volumes = [1000000] * n
    bars = []
    for i in range(n):
        c = closes[i] if i < len(closes) else 100.0
        v = volumes[i] if i < len(volumes) else 1000000
        bars.append(KlineData(
            symbol="TEST.SH",
            trade_date=f"2026-08-{i+1:02d}",
            open=c * 0.99,
            high=c * 1.01,
            low=c * 0.98,
            close=c,
            volume=v,
            amount=c * v,
            change_pct=0.5,
            turnover=1.5,
            data_source="test",
        ))
    return bars


class TestTechnicalAnalysisService:
    def setup_method(self):
        self.ta = TechnicalAnalysisService()

    def test_empty_klines(self):
        result = self.ta.compute([])
        assert result.symbol == ""

    def test_insufficient_data(self):
        klines = _make_klines([100, 101, 102])
        result = self.ta.compute(klines)
        assert result.symbol == "TEST.SH"
        assert result.ma5 == 0.0  # Not enough bars
        assert result.rsi == 0.0

    def test_ma_computation(self):
        closes = [100 + i * 0.5 for i in range(30)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        assert result.ma5 > 0
        assert result.ma10 > 0
        assert result.ma20 > 0
        assert result.ma5 > result.ma20  # Rising trend

    def test_rsi_range(self):
        closes = [100 + i * 0.3 for i in range(30)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        assert 0 <= result.rsi <= 100

    def test_rsi_overbought(self):
        # Strong uptrend -> high RSI
        closes = [100 + i * 2 for i in range(30)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        assert result.rsi > 70

    def test_rsi_oversold(self):
        # Strong downtrend -> low RSI
        closes = [200 - i * 2 for i in range(30)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        assert result.rsi < 30

    def test_macd_computation(self):
        closes = [100 + i * 0.5 for i in range(50)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        assert result.macd_line != 0.0
        assert result.macd_signal != 0.0

    def test_kdj_computation(self):
        closes = [100 + i * 0.3 for i in range(20)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        assert 0 <= result.kdj_k <= 100
        assert 0 <= result.kdj_d <= 100

    def test_bollinger_computation(self):
        closes = [100 + (i % 5) * 0.5 for i in range(30)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        assert result.boll_upper > result.boll_middle > result.boll_lower

    def test_atr_positive(self):
        closes = [100 + i * 0.2 for i in range(30)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        assert result.atr > 0

    def test_volatility_positive(self):
        closes = [100 + (i % 3) * 1.0 for i in range(30)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        assert result.volatility > 0

    def test_volume_ma(self):
        closes = [100] * 25
        volumes = [1000000 + i * 10000 for i in range(25)]
        klines = _make_klines(closes, volumes)
        result = self.ta.compute(klines)
        assert result.volume_ma5 > 0
        assert result.volume_ma10 > 0
        assert result.volume_ma20 > 0

    def test_to_dict(self):
        closes = [100 + i * 0.5 for i in range(30)]
        klines = _make_klines(closes)
        result = self.ta.compute(klines)
        d = result.to_dict()
        assert "ma5" in d
        assert "rsi" in d
        assert "macd_line" in d
