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


class TestRiskEngineEnhanced:
    @pytest.mark.asyncio
    async def test_price_limit_main_board(self):
        engine = RiskEngine()
        result = await engine.check_order(
            symbol="600519.SH", side="BUY", price=150.0,
            quantity=100, order_amount=15000.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={}, pre_close=100.0, board="MAIN",
        )
        assert not result.passed
        assert any("price limit" in r.lower() or "outside" in r.lower() for r in result.rejection_reasons)

    @pytest.mark.asyncio
    async def test_price_limit_gem_board(self):
        engine = RiskEngine()
        result = await engine.check_order(
            symbol="300750.SZ", side="BUY", price=115.0,
            quantity=100, order_amount=11500.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={}, pre_close=100.0, board="GEM",
        )
        assert result.passed  # ±20% for GEM, 115 is within range

    @pytest.mark.asyncio
    async def test_price_limit_gem_board_exceeded(self):
        engine = RiskEngine()
        result = await engine.check_order(
            symbol="300750.SZ", side="BUY", price=125.0,
            quantity=100, order_amount=12500.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={}, pre_close=100.0, board="GEM",
        )
        assert not result.passed

    @pytest.mark.asyncio
    async def test_industry_exposure_limit(self):
        engine = RiskEngine()
        engine.add_industry_exposure("白酒", 395000)
        result = await engine.check_order(
            symbol="600519.SH", side="BUY", price=100.0,
            quantity=100, order_amount=10000.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={}, industry="白酒",
        )
        assert not result.passed
        assert any("industry" in r.lower() for r in result.rejection_reasons)

    @pytest.mark.asyncio
    async def test_cooldown_after_consecutive_losses(self):
        engine = RiskEngine()
        for _ in range(5):
            engine.record_trade_result(pnl=-1000)
        result = await engine.check_order(
            symbol="600519.SH", side="BUY", price=100.0,
            quantity=100, order_amount=10000.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={},
        )
        assert not result.passed
        assert any("cooldown" in r.lower() for r in result.rejection_reasons)

    @pytest.mark.asyncio
    async def test_cooldown_reset(self):
        engine = RiskEngine()
        for _ in range(5):
            engine.record_trade_result(pnl=-1000)
        engine.reset_cooldown()
        result = await engine.check_order(
            symbol="600519.SH", side="BUY", price=100.0,
            quantity=100, order_amount=10000.0,
            account_cash=500000.0, total_asset=1000000.0,
            current_positions={},
        )
        assert result.passed

    @pytest.mark.asyncio
    async def test_winning_streak_resets_cooldown(self):
        engine = RiskEngine()
        for _ in range(4):
            engine.record_trade_result(pnl=-1000)
        assert engine._consecutive_losses == 4
        engine.record_trade_result(pnl=500)
        assert engine._consecutive_losses == 0

    @pytest.mark.asyncio
    async def test_status_property(self):
        engine = RiskEngine()
        engine.add_industry_exposure("银行", 100000)
        status = engine.status
        assert "daily_orders" in status
        assert "consecutive_losses" in status
        assert "industry_exposure" in status
        assert status["industry_exposure"]["银行"] == 100000
