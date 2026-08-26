"""Bollinger Band mean reversion strategy – stub."""
from __future__ import annotations
from typing import Dict, List
from app.strategies.base import Strategy, StrategySignal

class BollingerStrategy(Strategy):
    @property
    def name(self) -> str:
        return "Bollinger"

    @property
    def version(self) -> str:
        return "v1"

    def universe(self) -> List[str]:
        return []

    def factors(self, symbol: str, data: dict) -> Dict[str, float]:
        return {}  # TODO: implement

    def signal(self, symbol: str, data: dict) -> StrategySignal:
        return StrategySignal(symbol=symbol, direction="HOLD", strategy_name=self.name)
