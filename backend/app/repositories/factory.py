"""
Repository factory – provides all repositories from a single session.

Usage:
    async with get_db_context() as session:
        repos = RepositoryFactory(session)
        user = await repos.users.get_by_username("admin")
        orders = await repos.orders.get_by_account(account_id)
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repo import UserRepository
from app.repositories.account_repo import AccountRepository
from app.repositories.stock_repo import StockRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.trade_repo import TradeRepository
from app.repositories.position_repo import PositionRepository
from app.repositories.signal_repo import SignalRepository
from app.repositories.kline_repo import KlineRepository


class RepositoryFactory:
    """Provides all repositories from a single database session."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._users = None
        self._accounts = None
        self._stocks = None
        self._orders = None
        self._trades = None
        self._positions = None
        self._signals = None
        self._klines = None

    @property
    def users(self) -> UserRepository:
        if self._users is None:
            self._users = UserRepository(self._session)
        return self._users

    @property
    def accounts(self) -> AccountRepository:
        if self._accounts is None:
            self._accounts = AccountRepository(self._session)
        return self._accounts

    @property
    def stocks(self) -> StockRepository:
        if self._stocks is None:
            self._stocks = StockRepository(self._session)
        return self._stocks

    @property
    def orders(self) -> OrderRepository:
        if self._orders is None:
            self._orders = OrderRepository(self._session)
        return self._orders

    @property
    def trades(self) -> TradeRepository:
        if self._trades is None:
            self._trades = TradeRepository(self._session)
        return self._trades

    @property
    def positions(self) -> PositionRepository:
        if self._positions is None:
            self._positions = PositionRepository(self._session)
        return self._positions

    @property
    def signals(self) -> SignalRepository:
        if self._signals is None:
            self._signals = SignalRepository(self._session)
        return self._signals

    @property
    def klines(self) -> KlineRepository:
        if self._klines is None:
            self._klines = KlineRepository(self._session)
        return self._klines
