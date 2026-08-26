"""
Integration tests for repositories using in-memory SQLite.

These tests validate the Repository pattern works correctly without
needing a running PostgreSQL instance.
"""
from __future__ import annotations

from datetime import datetime
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base
from app.models.user import User
from app.models.account import Account
from app.models.stock import Stock
from app.models.order import Order, OrderStatus
from app.models.trade import Trade
from app.models.position import Position
from app.models.signal import Signal
from app.models.kline import Kline
from app.repositories.factory import RepositoryFactory


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite async session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def repos(db_session: AsyncSession) -> RepositoryFactory:
    return RepositoryFactory(db_session)


@pytest_asyncio.fixture
async def sample_user(repos: RepositoryFactory) -> User:
    return await repos.users.create({
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": "hashed123",
        "role": "RESEARCH",
        "is_active": True,
    })


@pytest_asyncio.fixture
async def sample_account(repos: RepositoryFactory, sample_user: User) -> Account:
    return await repos.accounts.create({
        "user_id": sample_user.id,
        "name": "Test Paper Account",
        "account_type": "PAPER",
        "initial_capital": 1_000_000.0,
        "cash": 1_000_000.0,
        "total_asset": 1_000_000.0,
        "broker": "mock",
        "is_active": True,
    })


# ── User Repository Tests ───────────────────────────────────────────────────

class TestUserRepository:
    @pytest.mark.asyncio
    async def test_create_user(self, repos, sample_user):
        assert sample_user.username == "testuser"
        assert sample_user.email == "test@example.com"
        assert sample_user.id is not None

    @pytest.mark.asyncio
    async def test_get_by_username(self, repos, sample_user):
        found = await repos.users.get_by_username("testuser")
        assert found is not None
        assert found.id == sample_user.id

    @pytest.mark.asyncio
    async def test_get_by_email(self, repos, sample_user):
        found = await repos.users.get_by_email("test@example.com")
        assert found is not None

    @pytest.mark.asyncio
    async def test_username_not_found(self, repos):
        found = await repos.users.get_by_username("nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_username_exists(self, repos, sample_user):
        assert await repos.users.username_exists("testuser")
        assert not await repos.users.username_exists("nobody")

    @pytest.mark.asyncio
    async def test_update_user(self, repos, sample_user):
        updated = await repos.users.update(sample_user.id, {"full_name": "Updated Name"})
        assert updated.full_name == "Updated Name"

    @pytest.mark.asyncio
    async def test_get_active_users(self, repos, sample_user):
        users = await repos.users.get_active_users()
        assert len(users) == 1


# ── Account Repository Tests ────────────────────────────────────────────────

class TestAccountRepository:
    @pytest.mark.asyncio
    async def test_create_account(self, repos, sample_account):
        assert sample_account.cash == 1_000_000.0
        assert sample_account.account_type == "PAPER"

    @pytest.mark.asyncio
    async def test_get_by_user_id(self, repos, sample_user, sample_account):
        accounts = await repos.accounts.get_by_user_id(sample_user.id)
        assert len(accounts) == 1

    @pytest.mark.asyncio
    async def test_get_active_account(self, repos, sample_user, sample_account):
        found = await repos.accounts.get_active_account(sample_user.id, "PAPER")
        assert found is not None
        assert found.id == sample_account.id

    @pytest.mark.asyncio
    async def test_update_cash(self, repos, sample_account):
        updated = await repos.accounts.update_cash(sample_account.id, 500_000.0)
        assert updated.cash == 500_000.0

    @pytest.mark.asyncio
    async def test_add_realized_pnl(self, repos, sample_account):
        updated = await repos.accounts.add_realized_pnl(sample_account.id, 15000.0)
        assert updated.realized_pnl == 15000.0
        updated2 = await repos.accounts.add_realized_pnl(sample_account.id, 5000.0)
        assert updated2.realized_pnl == 20000.0


# ── Stock Repository Tests ──────────────────────────────────────────────────

class TestStockRepository:
    @pytest.mark.asyncio
    async def test_create_stock(self, repos):
        stock = await repos.stocks.create({
            "symbol": "600519.SH",
            "name": "贵州茅台",
            "market": "SH",
            "industry": "白酒",
            "is_active": True,
        })
        assert stock.symbol == "600519.SH"

    @pytest.mark.asyncio
    async def test_get_by_symbol(self, repos):
        await repos.stocks.create({"symbol": "600519.SH", "name": "贵州茅台", "market": "SH", "is_active": True})
        found = await repos.stocks.get_by_symbol("600519.SH")
        assert found is not None
        assert found.name == "贵州茅台"

    @pytest.mark.asyncio
    async def test_bulk_create(self, repos):
        stocks = [
            {"symbol": "600519.SH", "name": "贵州茅台", "market": "SH", "is_active": True},
            {"symbol": "000858.SZ", "name": "五粮液", "market": "SZ", "is_active": True},
            {"symbol": "300750.SZ", "name": "宁德时代", "market": "SZ", "is_active": True},
        ]
        count = await repos.stocks.bulk_create(stocks)
        assert count == 3
        # Duplicate should not create new
        count2 = await repos.stocks.bulk_create(stocks)
        assert count2 == 0

    @pytest.mark.asyncio
    async def test_search_by_name(self, repos):
        await repos.stocks.create({"symbol": "600519.SH", "name": "贵州茅台", "market": "SH", "is_active": True})
        await repos.stocks.create({"symbol": "000858.SZ", "name": "五粮液", "market": "SZ", "is_active": True})
        results = await repos.stocks.search_by_name("茅台")
        assert len(results) == 1
        assert results[0].symbol == "600519.SH"

    @pytest.mark.asyncio
    async def test_update_quote(self, repos):
        await repos.stocks.create({"symbol": "600519.SH", "name": "贵州茅台", "market": "SH", "is_active": True})
        updated = await repos.stocks.update_quote("600519.SH", 1450.0, 1000000, 1.45e9, "2026-08-26T09:30:00")
        assert updated.latest_price == 1450.0


# ── Order Repository Tests ──────────────────────────────────────────────────

class TestOrderRepository:
    @pytest.mark.asyncio
    async def test_create_order(self, repos, sample_account):
        order = await repos.orders.create({
            "account_id": sample_account.id,
            "symbol": "600519.SH",
            "side": "BUY",
            "order_type": "LIMIT",
            "price": 1450.0,
            "quantity": 100,
            "client_order_id": "ORDER-20260826-000001",
            "status": OrderStatus.PENDING.value,
        })
        assert order.symbol == "600519.SH"
        assert order.client_order_id == "ORDER-20260826-000001"

    @pytest.mark.asyncio
    async def test_get_by_client_order_id(self, repos, sample_account):
        await repos.orders.create({
            "account_id": sample_account.id,
            "symbol": "600519.SH",
            "side": "BUY",
            "quantity": 100,
            "client_order_id": "ORDER-20260826-000002",
            "status": OrderStatus.PENDING.value,
        })
        found = await repos.orders.get_by_client_order_id("ORDER-20260826-000002")
        assert found is not None

    @pytest.mark.asyncio
    async def test_duplicate_order_detection(self, repos, sample_account):
        await repos.orders.create({
            "account_id": sample_account.id,
            "symbol": "600519.SH",
            "side": "BUY",
            "quantity": 100,
            "client_order_id": "ORDER-20260826-000003",
            "status": OrderStatus.PENDING.value,
        })
        assert await repos.orders.client_order_id_exists("ORDER-20260826-000003")
        assert not await repos.orders.client_order_id_exists("ORDER-99999999-999999")

    @pytest.mark.asyncio
    async def test_update_order_status(self, repos, sample_account):
        order = await repos.orders.create({
            "account_id": sample_account.id,
            "symbol": "600519.SH",
            "side": "BUY",
            "quantity": 100,
            "client_order_id": "ORDER-20260826-000004",
            "status": OrderStatus.PENDING.value,
        })
        updated = await repos.orders.update_status(
            order.id,
            OrderStatus.FILLED.value,
            broker_order_id="BROKER-123",
            filled_quantity=100,
            avg_fill_price=1450.0,
        )
        assert updated.status == OrderStatus.FILLED.value
        assert updated.broker_order_id == "BROKER-123"


# ── Position Repository Tests ───────────────────────────────────────────────

class TestPositionRepository:
    @pytest.mark.asyncio
    async def test_create_position(self, repos, sample_account):
        pos = await repos.positions.create({
            "account_id": sample_account.id,
            "symbol": "600519.SH",
            "quantity": 100,
            "available_quantity": 0,  # T+1: not yet available
            "avg_cost": 1450.0,
            "current_price": 1460.0,
            "market_value": 146000.0,
            "unrealized_pnl": 1000.0,
            "is_open": True,
        })
        assert pos.symbol == "600519.SH"
        assert pos.quantity == 100

    @pytest.mark.asyncio
    async def test_update_price(self, repos, sample_account):
        pos = await repos.positions.create({
            "account_id": sample_account.id,
            "symbol": "600519.SH",
            "quantity": 100,
            "available_quantity": 100,
            "avg_cost": 1450.0,
            "current_price": 1450.0,
            "market_value": 145000.0,
            "is_open": True,
        })
        updated = await repos.positions.update_price(pos.id, 1500.0)
        assert updated.current_price == 1500.0
        assert updated.market_value == 150000.0
        assert updated.unrealized_pnl == 5000.0

    @pytest.mark.asyncio
    async def test_get_open_positions(self, repos, sample_account):
        await repos.positions.create({
            "account_id": sample_account.id, "symbol": "600519.SH",
            "quantity": 100, "avg_cost": 1450.0, "current_price": 1450.0,
            "market_value": 145000.0, "is_open": True,
        })
        await repos.positions.create({
            "account_id": sample_account.id, "symbol": "000858.SZ",
            "quantity": 0, "avg_cost": 0, "current_price": 0,
            "market_value": 0, "is_open": False,
        })
        open_positions = await repos.positions.get_by_account(sample_account.id)
        assert len(open_positions) == 1  # Only open positions


# ── Kline Repository Tests ──────────────────────────────────────────────────

class TestKlineRepository:
    @pytest.mark.asyncio
    async def test_bulk_upsert(self, repos):
        klines = [
            {"symbol": "600519.SH", "trade_date": "2026-08-25", "timeframe": "D",
             "open": 1440.0, "high": 1460.0, "low": 1435.0, "close": 1455.0,
             "volume": 1000000, "data_source": "mock"},
            {"symbol": "600519.SH", "trade_date": "2026-08-26", "timeframe": "D",
             "open": 1455.0, "high": 1470.0, "low": 1450.0, "close": 1465.0,
             "volume": 1200000, "data_source": "mock"},
        ]
        count = await repos.klines.bulk_upsert(klines)
        assert count == 2
        # Upsert again – should update, not create new
        klines[0]["close"] = 1458.0
        count2 = await repos.klines.bulk_upsert(klines[:1])
        assert count2 == 1
        # Verify update
        closes = await repos.klines.get_closes("600519.SH")
        assert closes[0] == 1458.0

    @pytest.mark.asyncio
    async def test_get_closes(self, repos):
        for i in range(10):
            await repos.klines.create({
                "symbol": "600519.SH",
                "trade_date": f"2026-08-{15+i:02d}",
                "timeframe": "D",
                "open": 1400.0 + i,
                "high": 1410.0 + i,
                "low": 1395.0 + i,
                "close": 1405.0 + i,
                "volume": 1000000,
                "data_source": "mock",
            })
        closes = await repos.klines.get_closes("600519.SH", limit=10)
        assert len(closes) == 10
        assert closes[-1] == 1414.0  # Last close

    @pytest.mark.asyncio
    async def test_get_latest(self, repos):
        for i in range(5):
            await repos.klines.create({
                "symbol": "600519.SH",
                "trade_date": f"2026-08-{20+i:02d}",
                "timeframe": "D",
                "open": 1400.0, "high": 1410.0, "low": 1395.0,
                "close": 1405.0 + i, "volume": 1000000,
                "data_source": "mock",
            })
        latest = await repos.klines.get_latest("600519.SH")
        assert latest.trade_date == "2026-08-24"
        assert latest.close == 1409.0


# ── Signal Repository Tests ─────────────────────────────────────────────────

class TestSignalRepository:
    @pytest.mark.asyncio
    async def test_create_signal(self, repos):
        sig = await repos.signals.create({
            "symbol": "600519.SH",
            "direction": "BUY",
            "signal_type": "STRATEGY",
            "score": 82.0,
            "confidence": 0.76,
            "entry_price": 1450.0,
            "stop_loss": 1377.0,
            "take_profit": 1595.0,
            "strategy_name": "MACD",
            "signal_time": datetime(2026, 8, 26, 9, 35, 0),
            "status": "ACTIVE",
        })
        assert sig.symbol == "600519.SH"
        assert sig.score == 82.0

    @pytest.mark.asyncio
    async def test_get_active_signals(self, repos):
        await repos.signals.create({
            "symbol": "600519.SH", "direction": "BUY",
            "signal_type": "STRATEGY", "score": 80.0,
            "signal_time": datetime(2026, 8, 26, 9, 35, 0), "status": "ACTIVE",
        })
        await repos.signals.create({
            "symbol": "000858.SZ", "direction": "SELL",
            "signal_type": "AI", "score": 60.0,
            "signal_time": datetime(2026, 8, 25, 10, 0, 0), "status": "EXPIRED",
        })
        active = await repos.signals.get_active_signals()
        assert len(active) == 1
        assert active[0].status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_mark_executed(self, repos):
        sig = await repos.signals.create({
            "symbol": "600519.SH", "direction": "BUY",
            "signal_type": "STRATEGY", "score": 80.0,
            "signal_time": datetime(2026, 8, 26, 9, 35, 0), "status": "ACTIVE",
        })
        updated = await repos.signals.mark_executed(sig.id)
        assert updated.status == "EXECUTED"
