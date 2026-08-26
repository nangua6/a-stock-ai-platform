"""
Abstract strategy interface.

All strategies must implement this interface to be loaded into the strategy engine.
Strategies are deterministic – they compute signals from data, not from LLM.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class StrategySignal:
    """Output of a strategy's signal() method."""
    symbol: str = ""
    direction: str = "HOLD"  # BUY | SELL | HOLD
    strength: float = 0.0    # -1.0 (strong sell) to 1.0 (strong buy)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_target: Optional[float] = None  # fraction of portfolio
    reasons: List[str] = field(default_factory=list)
    strategy_name: str = ""
    strategy_version: str = "v1"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class Strategy(ABC):
    """
    Abstract strategy interface.

    A strategy is a deterministic plugin that:
    1. Defines its stock universe
    2. Computes technical/fundamental factors
    3. Generates BUY/SELL/HOLD signals
    4. Specifies position sizing and risk parameters
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Strategy version."""
        ...

    @abstractmethod
    def universe(self) -> List[str]:
        """Return the stock universe this strategy covers."""
        ...

    @abstractmethod
    def factors(self, symbol: str, data: dict) -> Dict[str, float]:
        """Compute the factors used by this strategy for a given symbol."""
        ...

    @abstractmethod
    def signal(self, symbol: str, data: dict) -> StrategySignal:
        """Generate a trading signal for a given symbol."""
        ...

    def position_size(self, signal: StrategySignal, account: dict) -> float:
        """Calculate position size (number of shares) given a signal and account state."""
        if signal.direction == "HOLD":
            return 0.0
        target_value = account.get("total_asset", 0) * (signal.position_target or 0.05)
        if signal.entry_price and signal.entry_price > 0:
            shares = target_value / signal.entry_price
            return int(shares / 100) * 100  # Round down to nearest lot
        return 0.0

    def risk_params(self, signal: StrategySignal) -> dict:
        """Return risk parameters for this signal."""
        return {
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "max_holding_days": 20,
        }
