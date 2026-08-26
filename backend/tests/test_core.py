"""Tests for core modules."""
import pytest
from app.core.security import Role, has_permission, hash_password, verify_password
from app.core.exceptions import (
    KillSwitchActiveError,
    RiskCheckFailedError,
    DuplicateOrderError,
)


class TestRBAC:
    def test_admin_has_all_permissions(self):
        for role in Role:
            if role != Role.ADMIN:
                assert has_permission(Role.ADMIN, role)

    def test_research_cannot_trade(self):
        assert not has_permission(Role.RESEARCH, Role.LIVE_TRADE)
        assert not has_permission(Role.RESEARCH, Role.PAPER_TRADING)

    def test_paper_trading_has_research(self):
        assert has_permission(Role.PAPER_TRADING, Role.RESEARCH)

    def test_live_trade_hierarchy(self):
        assert has_permission(Role.LIVE_TRADE, Role.LIVE_VIEW)
        assert has_permission(Role.LIVE_TRADE, Role.PAPER_TRADING)
        assert has_permission(Role.LIVE_TRADE, Role.RESEARCH)
        assert not has_permission(Role.LIVE_TRADE, Role.AUTO_TRADE)


class TestPassword:
    def test_hash_and_verify(self):
        hashed = hash_password("test123")
        assert verify_password("test123", hashed)
        assert not verify_password("wrong", hashed)


class TestExceptions:
    def test_kill_switch_error(self):
        err = KillSwitchActiveError()
        assert err.code == "KILL_SWITCH_ACTIVE"
        assert err.status_code == 403

    def test_risk_check_failed(self):
        err = RiskCheckFailedError("max position exceeded")
        assert "max position" in err.message
        assert err.code == "RISK_CHECK_FAILED"
