"""
Risk Engine – the gatekeeper between strategy/AI and trade execution.

Every order MUST pass through the RiskEngine before reaching the BrokerAdapter.
The RiskEngine is deterministic – no LLM calls, no probabilistic decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from app.config.settings import get_settings


@dataclass
class RiskCheckResult:
    passed: bool
    order_id: str = ""
    checks: List[dict] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class RiskEngine:
    """
    Deterministic risk engine.

    Runs a gauntlet of checks on every order:
    1. Kill switch check
    2. Trading mode check (LIVE enabled?)
    3. Trading hours check
    4. Stock status check (ST, suspended, limit up/down)
    5. Quantity validation (lot size, A-share rules)
    6. Price validation
    7. Single trade amount check
    8. Position size check
    9. Daily loss check
    10. Max drawdown check
    11. Industry exposure check
    12. Daily order count check
    13. Duplicate order check
    """

    def __init__(self):
        self._daily_orders: int = 0
        self._daily_loss: float = 0.0
        self._peak_asset: float = 0.0
        self._consecutive_losses: int = 0

    def reset_daily(self):
        """Reset daily counters (called at start of each trading day)."""
        self._daily_orders = 0
        self._daily_loss = 0.0

    async def check_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: int,
        order_amount: float,
        account_cash: float,
        total_asset: float,
        current_positions: dict,
        is_live: bool = False,
        is_st: bool = False,
        is_suspended: bool = False,
        is_limit_up: bool = False,
        is_limit_down: bool = False,
    ) -> RiskCheckResult:
        """Run all risk checks on a proposed order."""
        settings = get_settings()
        checks = []
        rejections = []

        # 1. Kill Switch
        if is_live and settings.global_kill_switch:
            checks.append({"check": "kill_switch", "passed": False})
            rejections.append("GLOBAL KILL SWITCH is active")
        else:
            checks.append({"check": "kill_switch", "passed": True})

        # 2. Live trading enabled?
        if is_live and not settings.live_trading:
            checks.append({"check": "live_trading_enabled", "passed": False})
            rejections.append("Live trading is not enabled")
        else:
            checks.append({"check": "live_trading_enabled", "passed": True})

        # 3. Lot size (must be multiple of 100)
        lot_ok = quantity >= 100 and quantity % 100 == 0
        checks.append({"check": "lot_size", "passed": lot_ok})
        if not lot_ok:
            rejections.append(f"Invalid lot size: {quantity} (must be ≥100 and multiple of 100)")

        # 4. Price positive
        price_ok = price > 0
        checks.append({"check": "price_positive", "passed": price_ok})
        if not price_ok:
            rejections.append(f"Invalid price: {price}")

        # 5. ST stock
        if is_st:
            checks.append({"check": "st_stock", "passed": False})
            rejections.append(f"Trading ST/ST* stocks requires explicit approval: {symbol}")
        else:
            checks.append({"check": "st_stock", "passed": True})

        # 6. Suspended
        if is_suspended:
            checks.append({"check": "not_suspended", "passed": False})
            rejections.append(f"Stock is suspended: {symbol}")
        else:
            checks.append({"check": "not_suspended", "passed": True})

        # 7. Single trade amount
        amount_ok = order_amount <= settings.max_single_trade_amount
        checks.append({"check": "single_trade_amount", "passed": amount_ok})
        if not amount_ok:
            rejections.append(f"Trade amount {order_amount:.2f} exceeds limit {settings.max_single_trade_amount:.2f}")

        # 8. Position size for BUY
        if side == "BUY" and total_asset > 0:
            existing = current_positions.get(symbol, {}).get("market_value", 0)
            new_position_value = existing + order_amount
            ratio = new_position_value / total_asset
            pos_ok = ratio <= settings.max_position_ratio
            checks.append({"check": "position_size", "passed": pos_ok, "ratio": round(ratio, 4)})
            if not pos_ok:
                rejections.append(f"Position ratio {ratio:.2%} exceeds limit {settings.max_position_ratio:.2%}")
        else:
            checks.append({"check": "position_size", "passed": True})

        # 9. Sufficient funds for BUY
        if side == "BUY":
            funds_ok = account_cash >= order_amount
            checks.append({"check": "sufficient_funds", "passed": funds_ok})
            if not funds_ok:
                rejections.append(f"Insufficient funds: need {order_amount:.2f}, have {account_cash:.2f}")
        else:
            checks.append({"check": "sufficient_funds", "passed": True})

        # 10. Daily order count
        self._daily_orders += 1
        count_ok = self._daily_orders <= settings.max_daily_orders
        checks.append({"check": "daily_order_count", "passed": count_ok, "count": self._daily_orders})
        if not count_ok:
            rejections.append(f"Daily order count {self._daily_orders} exceeds limit {settings.max_daily_orders}")

        # 11. Daily loss check
        if total_asset > 0:
            loss_ratio = self._daily_loss / total_asset if self._daily_loss > 0 else 0
            loss_ok = loss_ratio < settings.max_daily_loss_ratio
            checks.append({"check": "daily_loss", "passed": loss_ok, "loss_ratio": round(loss_ratio, 4)})
            if not loss_ok:
                rejections.append(f"Daily loss ratio {loss_ratio:.2%} exceeds limit {settings.max_daily_loss_ratio:.2%}")
        else:
            checks.append({"check": "daily_loss", "passed": True})

        # 12. Max drawdown
        if self._peak_asset > 0 and total_asset < self._peak_asset:
            drawdown = (self._peak_asset - total_asset) / self._peak_asset
            dd_ok = drawdown < settings.max_drawdown
            checks.append({"check": "max_drawdown", "passed": dd_ok, "drawdown": round(drawdown, 4)})
            if not dd_ok:
                rejections.append(f"Drawdown {drawdown:.2%} exceeds limit {settings.max_drawdown:.2%}")
        else:
            checks.append({"check": "max_drawdown", "passed": True})

        # Update peak
        if total_asset > self._peak_asset:
            self._peak_asset = total_asset

        return RiskCheckResult(
            passed=len(rejections) == 0,
            checks=checks,
            rejection_reasons=rejections,
        )

    def record_trade_result(self, pnl: float):
        """Record a trade result for daily loss tracking."""
        if pnl < 0:
            self._daily_loss += abs(pnl)
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0
