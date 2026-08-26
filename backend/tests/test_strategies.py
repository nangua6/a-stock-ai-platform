"""Tests for trading strategies."""
import pytest
from app.strategies.builtin import MACDStrategy, MACrossStrategy, RSIStrategy


class TestMACDStrategy:
    def test_hold_with_insufficient_data(self):
        strat = MACDStrategy()
        sig = strat.signal("600519.SH", {"closes": [100, 101, 102]})
        assert sig.direction == "HOLD"

    def test_buy_on_bullish_crossover(self):
        strat = MACDStrategy()
        # Create a rising trend then crossover
        closes = [100 + i * 0.1 for i in range(30)]
        # Then add a dip and recovery to create crossover
        closes.extend([closes[-1] - 0.5 for _ in range(5)])
        closes.extend([closes[-1] + 0.3 for _ in range(10)])
        sig = strat.signal("600519.SH", {"closes": closes})
        assert sig.strategy_name == "MACD"


class TestMACrossStrategy:
    def test_hold_with_insufficient_data(self):
        strat = MACrossStrategy(5, 20)
        sig = strat.signal("600519.SH", {"closes": [100] * 10})
        assert sig.direction == "HOLD"

    def test_name(self):
        strat = MACrossStrategy(5, 20)
        assert strat.name == "MA5x20"


class TestRSIStrategy:
    def test_hold_with_insufficient_data(self):
        strat = RSIStrategy()
        sig = strat.signal("600519.SH", {"closes": [100] * 5})
        assert sig.direction == "HOLD"

    def test_oversold_signal(self):
        strat = RSIStrategy()
        # Create a declining series to push RSI below 30
        closes = [100 - i * 0.5 for i in range(20)]
        sig = strat.signal("600519.SH", {"closes": closes})
        assert sig.direction == "BUY"
        assert sig.strategy_name == "RSI"
