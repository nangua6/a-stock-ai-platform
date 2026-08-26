"""Tests for ScreeningEngine."""
import pytest
from app.services.screening_engine import (
    ScreeningEngine,
    ScreeningRule,
    FactorDirection,
)
from app.market.base import QuoteData, KlineData


def _make_quote(symbol="TEST.SH", price=100, change_pct=1.5, volume=1000000, amount=1e8):
    return QuoteData(
        symbol=symbol, name="Test", price=price, change_pct=change_pct,
        volume=volume, amount=amount, data_source="test",
    )


def _make_klines(n=30, base_price=100, trend=0.5):
    bars = []
    for i in range(n):
        c = base_price + i * trend
        bars.append(KlineData(
            symbol="TEST.SH", trade_date=f"2026-08-{i+1:02d}",
            open=c * 0.99, high=c * 1.01, low=c * 0.98, close=c,
            volume=1000000 + i * 10000, amount=c * 1000000,
            change_pct=trend / c * 100, turnover=1.5, data_source="test",
        ))
    return bars


class TestScreeningEngine:
    def setup_method(self):
        self.engine = ScreeningEngine()

    def test_compute_factors(self):
        quote = _make_quote()
        klines = _make_klines()
        factors = self.engine.compute_factors(quote, klines)
        assert "price" in factors
        assert "rsi" in factors
        assert "ma5" in factors
        assert "momentum_5d" in factors

    def test_screen_passes_good_stock(self):
        candidates = [{
            "symbol": "TEST.SH", "name": "Test",
            "quote": _make_quote(change_pct=2.0),
            "klines": _make_klines(trend=1.0),
        }]
        rules = [
            ScreeningRule(name="positive", factor="momentum_5d", min_value=0.0, weight=1.0),
        ]
        result = self.engine.screen(candidates, rules)
        assert result.total_passed == 1
        assert result.candidates[0].symbol == "TEST.SH"

    def test_screen_filters_bad_stock(self):
        candidates = [{
            "symbol": "BAD.SH", "name": "Bad",
            "quote": _make_quote(change_pct=-3.0),
            "klines": _make_klines(trend=-2.0),
        }]
        rules = [
            ScreeningRule(name="positive", factor="momentum_5d", min_value=0.0, weight=1.0),
        ]
        result = self.engine.screen(candidates, rules)
        assert result.total_passed == 0

    def test_screen_ranks_by_score(self):
        candidates = [
            {"symbol": "A.SH", "name": "A",
             "quote": _make_quote(change_pct=1.0),
             "klines": _make_klines(trend=0.5)},
            {"symbol": "B.SH", "name": "B",
             "quote": _make_quote(change_pct=3.0),
             "klines": _make_klines(trend=2.0)},
        ]
        rules = [
            ScreeningRule(name="momentum", factor="momentum_5d", min_value=0.0, weight=2.0),
        ]
        result = self.engine.screen(candidates, rules, top_n=10)
        assert result.total_passed == 2
        # B should rank higher (more momentum)
        assert result.candidates[0].symbol == "B.SH"

    def test_screen_with_max_value(self):
        # Fluctuating prices give moderate RSI (around 50)
        klines = []
        for i in range(30):
            c = 100.0 + (i % 4 - 1.5) * 0.5  # oscillates around 100
            klines.append(KlineData(
                symbol="TEST.SH", trade_date=f"2026-08-{i+1:02d}",
                open=c * 0.99, high=c * 1.01, low=c * 0.98, close=c,
                volume=1000000, amount=c * 1000000,
                change_pct=0.1, turnover=1.5, data_source="test",
            ))
        candidates = [{
            "symbol": "TEST.SH", "name": "Test",
            "quote": _make_quote(),
            "klines": klines,
        }]
        rules = [
            ScreeningRule(name="rsi_ok", factor="rsi", max_value=70.0, weight=1.0),
        ]
        result = self.engine.screen(candidates, rules)
        assert result.total_passed == 1

    def test_screen_top_n(self):
        candidates = [
            {"symbol": f"{i}.SH", "name": f"Stock {i}",
             "quote": _make_quote(change_pct=float(i)),
             "klines": _make_klines(trend=float(i) * 0.3)}
            for i in range(1, 11)
        ]
        rules = [
            ScreeningRule(name="momentum", factor="momentum_5d", min_value=0.0, weight=1.0),
        ]
        result = self.engine.screen(candidates, rules, top_n=3)
        assert len(result.candidates) <= 3
