"""Tests for RiskEngine stale data protection."""
import pytest
from app.risk.engine import RiskEngine, MAX_QUOTE_AGE_SECONDS


class TestRiskEngineStaleData:
    @pytest.mark.asyncio
    async def test_pass_with_fresh_data(self):
        engine = RiskEngine()
        result = await engine.check_order(
            symbol="600519.SH", side="BUY", price=100.0,
            quantity=100, order_amount=10000.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={},
            data_age_seconds=5.0, is_data_available=True,
        )
        assert result.passed

    @pytest.mark.asyncio
    async def test_fail_with_stale_data(self):
        engine = RiskEngine()
        result = await engine.check_order(
            symbol="600519.SH", side="BUY", price=100.0,
            quantity=100, order_amount=10000.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={},
            data_age_seconds=600.0,  # 10 minutes > 5 min limit
            is_data_available=True,
        )
        assert not result.passed
        assert any("stale" in r.lower() for r in result.rejection_reasons)

    @pytest.mark.asyncio
    async def test_fail_with_unavailable_data(self):
        engine = RiskEngine()
        result = await engine.check_order(
            symbol="600519.SH", side="BUY", price=100.0,
            quantity=100, order_amount=10000.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={},
            is_data_available=False,
        )
        assert not result.passed
        assert any("unavailable" in r.lower() for r in result.rejection_reasons)

    @pytest.mark.asyncio
    async def test_stale_check_details(self):
        engine = RiskEngine()
        result = await engine.check_order(
            symbol="600519.SH", side="BUY", price=100.0,
            quantity=100, order_amount=10000.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={},
            data_age_seconds=600.0, is_data_available=True,
        )
        stale_check = next(c for c in result.checks if c["check"] == "stale_data")
        assert not stale_check["passed"]
        assert stale_check["data_age_seconds"] == 600.0

    @pytest.mark.asyncio
    async def test_no_age_info_passes(self):
        """When no age info is provided, stale check is skipped."""
        engine = RiskEngine()
        result = await engine.check_order(
            symbol="600519.SH", side="BUY", price=100.0,
            quantity=100, order_amount=10000.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={},
        )
        assert result.passed
        stale_check = next(c for c in result.checks if c["check"] == "stale_data")
        assert stale_check["passed"]
