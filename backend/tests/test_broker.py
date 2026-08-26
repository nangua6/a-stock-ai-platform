"""Tests for broker adapters."""
import pytest
from app.broker.mock_broker import MockBroker
from app.broker.paper_broker import PaperBroker
from app.broker.base import OrderRequest


@pytest.mark.asyncio
async def test_mock_broker_place_order():
    broker = MockBroker()
    result = await broker.place_order(OrderRequest(
        symbol="600519.SH", side="BUY", price=1450.0, quantity=100
    ))
    assert result.success
    assert result.broker_order_id.startswith("MOCK-")


@pytest.mark.asyncio
async def test_mock_broker_positions():
    broker = MockBroker()
    await broker.place_order(OrderRequest(
        symbol="600519.SH", side="BUY", price=1450.0, quantity=100
    ))
    positions = await broker.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "600519.SH"


@pytest.mark.asyncio
async def test_paper_broker_lot_size_validation():
    broker = PaperBroker()
    result = await broker.place_order(OrderRequest(
        symbol="600519.SH", side="BUY", price=1450.0, quantity=50  # Invalid
    ))
    assert not result.success
    assert result.error_code == "INVALID_LOT_SIZE"


@pytest.mark.asyncio
async def test_paper_broker_insufficient_funds():
    broker = PaperBroker(initial_capital=10000)
    result = await broker.place_order(OrderRequest(
        symbol="600519.SH", side="BUY", price=1450.0, quantity=100  # Costs 145k+
    ))
    assert not result.success
    assert result.error_code == "INSUFFICIENT_FUNDS"
