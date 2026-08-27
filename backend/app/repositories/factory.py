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
from app.repositories.sync_job_repo import SyncJobRepository
from app.repositories.technical_snapshot_repo import TechnicalSnapshotRepository
from app.repositories.analysis_snapshot_repo import AnalysisSnapshotRepository
from app.repositories.watchlist_repo import WatchlistRepository


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
        self._sync_jobs = None
        self._technical_snapshots = None
        self._analysis_snapshots = None
        self._watchlist = None

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

    @property
    def sync_jobs(self) -> SyncJobRepository:
        if self._sync_jobs is None:
            self._sync_jobs = SyncJobRepository(self._session)
        return self._sync_jobs

    @property
    def technical_snapshots(self) -> TechnicalSnapshotRepository:
        if self._technical_snapshots is None:
            self._technical_snapshots = TechnicalSnapshotRepository(self._session)
        return self._technical_snapshots

    @property
    def analysis_snapshots(self) -> AnalysisSnapshotRepository:
        if self._analysis_snapshots is None:
            self._analysis_snapshots = AnalysisSnapshotRepository(self._session)
        return self._analysis_snapshots

    @property
    def watchlist(self) -> WatchlistRepository:
        if self._watchlist is None:
            self._watchlist = WatchlistRepository(self._session)
        return self._watchlist
