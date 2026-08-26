"""Tests for DataQualityService."""
from __future__ import annotations

import pytest

from app.market.base import KlineData, QuoteData
from app.services.data_quality import DataQualityService, ValidationResult


@pytest.fixture
def quality():
    return DataQualityService()


class TestSymbolValidation:
    def test_valid_sh(self, quality):
        assert quality.validate_symbol("600519.SH") is True

    def test_valid_sz(self, quality):
        assert quality.validate_symbol("000001.SZ") is True

    def test_valid_bj(self, quality):
        assert quality.validate_symbol("430047.BJ") is True

    def test_valid_no_suffix(self, quality):
        assert quality.validate_symbol("600519") is True

    def test_invalid_letters(self, quality):
        assert quality.validate_symbol("ABCDEF.SH") is False

    def test_invalid_short(self, quality):
        assert quality.validate_symbol("60051") is False

    def test_empty(self, quality):
        assert quality.validate_symbol("") is False


class TestQuoteValidation:
    def _make_quote(self, **overrides) -> QuoteData:
        base = QuoteData(
            symbol="600519.SH",
            name="贵州茅台",
            price=1450.0,
            volume=100000,
            amount=145000000.0,
            timestamp="2024-01-15T10:30:00",
            data_source="akshare",
        )
        for k, v in overrides.items():
            setattr(base, k, v)
        return base

    def test_valid_quote(self, quality):
        q = self._make_quote()
        result = quality.validate_quote(q)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_missing_symbol(self, quality):
        q = self._make_quote(symbol="")
        result = quality.validate_quote(q)
        assert result.is_valid is False
        assert any(e.field == "symbol" for e in result.errors)

    def test_invalid_symbol_format(self, quality):
        q = self._make_quote(symbol="INVALID")
        result = quality.validate_quote(q)
        assert result.is_valid is False

    def test_zero_price(self, quality):
        q = self._make_quote(price=0.0)
        result = quality.validate_quote(q)
        assert result.is_valid is False
        assert any(e.field == "price" for e in result.errors)

    def test_negative_price(self, quality):
        q = self._make_quote(price=-10.0)
        result = quality.validate_quote(q)
        assert result.is_valid is False

    def test_negative_volume(self, quality):
        q = self._make_quote(volume=-100)
        result = quality.validate_quote(q)
        assert result.is_valid is False

    def test_zero_volume_ok(self, quality):
        q = self._make_quote(volume=0)
        result = quality.validate_quote(q)
        assert result.is_valid is True

    def test_missing_timestamp(self, quality):
        q = self._make_quote(timestamp="")
        result = quality.validate_quote(q)
        assert result.is_valid is False

    def test_missing_data_source(self, quality):
        q = self._make_quote(data_source="")
        result = quality.validate_quote(q)
        assert result.is_valid is False


class TestKlineValidation:
    def _make_kline(self, **overrides) -> KlineData:
        base = KlineData(
            symbol="600519.SH",
            trade_date="2024-01-15",
            timeframe="D",
            open=1440.0,
            high=1460.0,
            low=1430.0,
            close=1450.0,
            volume=100000,
            amount=145000000.0,
            data_source="akshare",
        )
        for k, v in overrides.items():
            setattr(base, k, v)
        return base

    def test_valid_kline(self, quality):
        k = self._make_kline()
        result = quality.validate_kline(k)
        assert result.is_valid is True

    def test_missing_symbol(self, quality):
        k = self._make_kline(symbol="")
        result = quality.validate_kline(k)
        assert result.is_valid is False

    def test_missing_trade_date(self, quality):
        k = self._make_kline(trade_date="")
        result = quality.validate_kline(k)
        assert result.is_valid is False

    def test_invalid_date_format(self, quality):
        k = self._make_kline(trade_date="20240115")
        result = quality.validate_kline(k)
        assert result.is_valid is False

    def test_zero_open(self, quality):
        k = self._make_kline(open=0.0)
        result = quality.validate_kline(k)
        assert result.is_valid is False

    def test_zero_close(self, quality):
        k = self._make_kline(close=0.0)
        result = quality.validate_kline(k)
        assert result.is_valid is False

    def test_high_less_than_low(self, quality):
        k = self._make_kline(high=1400.0, low=1500.0)
        result = quality.validate_kline(k)
        assert result.is_valid is False
        assert any(e.field == "high_low" for e in result.errors)

    def test_negative_volume(self, quality):
        k = self._make_kline(volume=-100)
        result = quality.validate_kline(k)
        assert result.is_valid is False

    def test_missing_data_source(self, quality):
        k = self._make_kline(data_source="")
        result = quality.validate_kline(k)
        assert result.is_valid is False


class TestBatchValidation:
    def test_all_valid(self, quality):
        klines = [
            KlineData(symbol="600519.SH", trade_date=f"2024-01-{i:02d}", open=100, high=110, low=90, close=105, volume=1000, data_source="test")
            for i in range(1, 4)
        ]
        result = quality.validate_klines(klines)
        assert result["total"] == 3
        assert result["valid"] == 3
        assert result["invalid"] == 0

    def test_some_invalid(self, quality):
        klines = [
            KlineData(symbol="600519.SH", trade_date="2024-01-01", open=100, high=110, low=90, close=105, volume=1000, data_source="test"),
            KlineData(symbol="", trade_date="2024-01-02", open=100, high=110, low=90, close=105, volume=1000, data_source="test"),  # bad symbol
        ]
        result = quality.validate_klines(klines)
        assert result["total"] == 2
        assert result["valid"] == 1
        assert result["invalid"] == 1

    def test_empty_list(self, quality):
        result = quality.validate_klines([])
        assert result["total"] == 0
        assert result["valid"] == 0
