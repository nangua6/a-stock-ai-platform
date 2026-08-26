"""Tests for the risk engine."""
import pytest
from app.risk.engine import RiskEngine


@pytest.mark.asyncio
async def test_risk_pass_normal_order():
    engine = RiskEngine()
    result = await engine.check_order(
        symbol="600519.SH",
        side="BUY",
        price=100.0,
        quantity=100,
        order_amount=10000.0,
        account_cash=500000.0,
        total_asset=1000000.0,
        current_positions={},
    )
    assert result.passed


@pytest.mark.asyncio
async def test_risk_fail_insufficient_funds():
    engine = RiskEngine()
    result = await engine.check_order(
        symbol="600519.SH",
        side="BUY",
        price=100.0,
        quantity=100,
        order_amount=10000.0,
        account_cash=5000.0,
        total_asset=1000000.0,
        current_positions={},
    )
    assert not result.passed
    assert any("Insufficient" in r for r in result.rejection_reasons)


@pytest.mark.asyncio
async def test_risk_fail_lot_size():
    engine = RiskEngine()
    result = await engine.check_order(
        symbol="600519.SH",
        side="BUY",
        price=100.0,
        quantity=50,  # Not a multiple of 100
        order_amount=5000.0,
        account_cash=500000.0,
        total_asset=1000000.0,
        current_positions={},
    )
    assert not result.passed


@pytest.mark.asyncio
async def test_risk_fail_single_trade_amount():
    engine = RiskEngine()
    result = await engine.check_order(
        symbol="600519.SH",
        side="BUY",
        price=1000.0,
        quantity=1000,
        order_amount=1000000.0,  # Exceeds default 100k limit
        account_cash=5000000.0,
        total_asset=10000000.0,
        current_positions={},
    )
    assert not result.passed
