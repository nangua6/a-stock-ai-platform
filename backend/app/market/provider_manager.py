"""
Provider Manager – composite provider with fallback chain and caching.

Usage:
    manager = ProviderManager(providers=[akshare, mock], cache=cache)
    quote = await manager.get_realtime_quote("600519.SH")
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_data_logger
from app.market.base import (
    DataAvailability,
    DataFreshness,
    DataSourceStatus,
    FinancialData,
    KlineData,
    MarketDataProvider,
    QuoteData,
)
from app.market.cache import MarketDataCache

logger = get_data_logger()


class ProviderManager(MarketDataProvider):
    """
    Composite provider that tries providers in order and falls back on failure.
    """

    def __init__(
        self,
        providers: List[MarketDataProvider],
        cache: Optional[MarketDataCache] = None,
        allow_mock_in_production: bool = False,
    ):
        if not providers:
            raise ValueError("At least one provider is required")
        self._providers = providers
        self._cache = cache or MarketDataCache()
        self._allow_mock = allow_mock_in_production
        self._status: Dict[str, DataSourceStatus] = {
            p.name: DataSourceStatus(provider=p.name) for p in providers
        }

    @property
    def name(self) -> str:
        return "provider_manager"

    @property
    def primary_provider(self) -> str:
        return self._providers[0].name

    @property
    def provider_names(self) -> List[str]:
        return [p.name for p in self._providers]

    def get_provider_status(self) -> List[dict]:
        return [s.to_dict() for s in self._status.values()]

    def _record_success(self, provider_name: str) -> None:
        status = self._status[provider_name]
        status.is_healthy = True
        status.last_success = datetime.now(timezone.utc).isoformat()
        status.consecutive_failures = 0
        status.total_requests += 1

    def _record_failure(self, provider_name: str, error: str) -> None:
        status = self._status[provider_name]
        status.last_failure = datetime.now(timezone.utc).isoformat()
        status.last_error = error
        status.consecutive_failures += 1
        status.total_requests += 1
        status.total_failures += 1
        if status.consecutive_failures >= 3:
            status.is_healthy = False

    async def _try_providers(
        self,
        operation: str,
        data_type: str,
        cache_key: str,
        func_name: str,
        **kwargs,
    ) -> tuple:
        """Try the operation across providers. Returns (result, DataAvailability)."""
        # Check cache first
        cache_entry = self._cache.get(data_type, cache_key)
        if cache_entry and cache_entry.freshness == DataFreshness.FRESH:
            availability = DataAvailability(
                is_available=True,
                freshness=DataFreshness.FRESH,
                provider=cache_entry.provider,
                data_timestamp=cache_entry.data_timestamp,
                fetched_at=cache_entry.fetched_at_iso,
                data_age_seconds=cache_entry.age,
            )
            return cache_entry.data, availability

        errors = []
        for provider in self._providers:
            provider_name = provider.name
            func = getattr(provider, func_name, None)
            if func is None:
                continue

            start = time.time()
            try:
                result = await func(**kwargs)
                elapsed = time.time() - start
                self._record_success(provider_name)

                now_iso = datetime.now(timezone.utc).isoformat()
                self._cache.put(
                    data_type=data_type,
                    data=result,
                    symbol=cache_key,
                    provider=provider_name,
                    data_timestamp=now_iso,
                )

                availability = DataAvailability(
                    is_available=True,
                    freshness=DataFreshness.FRESH,
                    provider=provider_name,
                    data_timestamp=now_iso,
                    fetched_at=now_iso,
                    data_age_seconds=0.0,
                )

                logger.info(
                    "market_data_fetched",
                    operation=operation,
                    provider=provider_name,
                    symbol=cache_key,
                    latency_ms=round(elapsed * 1000, 1),
                )
                return result, availability

            except Exception as e:
                elapsed = time.time() - start
                error_type = type(e).__name__
                self._record_failure(provider_name, str(e))
                errors.append((provider_name, error_type, str(e)))

                logger.warning(
                    "market_data_failed",
                    operation=operation,
                    provider=provider_name,
                    symbol=cache_key,
                    error_type=error_type,
                    error=str(e)[:200],
                    latency_ms=round(elapsed * 1000, 1),
                )

        availability = DataAvailability(
            is_available=False,
            freshness=DataFreshness.UNAVAILABLE,
            provider="none",
            error_message=f"All providers failed: {errors}",
            error_type="ALL_PROVIDERS_FAILED",
        )
        return None, availability

    # ── Delegated operations ───────────────────────────────────────────────

    async def get_realtime_quote(self, symbol: str) -> QuoteData:
        result, _ = await self._try_providers(
            operation="get_realtime_quote",
            data_type="quote",
            cache_key=symbol,
            func_name="get_realtime_quote",
            symbol=symbol,
        )
        if result is None:
            return QuoteData(symbol=symbol, data_source="unavailable")
        return result

    async def get_realtime_quotes(self, symbols: List[str]) -> List[QuoteData]:
        for provider in self._providers:
            try:
                result = await provider.get_realtime_quotes(symbols)
                self._record_success(provider.name)
                return result
            except Exception as e:
                self._record_failure(provider.name, str(e))
                logger.warning("batch_quote_failed", provider=provider.name, error=str(e)[:200])

        results = []
        for sym in symbols:
            try:
                q = await self.get_realtime_quote(sym)
                results.append(q)
            except Exception:
                pass
        return results

    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "D",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[KlineData]:
        cache_type = f"kline_{timeframe.lower()}"
        result, _ = await self._try_providers(
            operation="get_kline",
            data_type=cache_type,
            cache_key=symbol,
            func_name="get_kline",
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return result or []

    async def get_financial_data(self, symbol: str) -> FinancialData:
        result, _ = await self._try_providers(
            operation="get_financial_data",
            data_type="financial",
            cache_key=symbol,
            func_name="get_financial_data",
            symbol=symbol,
        )
        return result or FinancialData(symbol=symbol, data_source="unavailable")

    async def get_stock_list(self, market: Optional[str] = None) -> List[dict]:
        result, _ = await self._try_providers(
            operation="get_stock_list",
            data_type="stock_list",
            cache_key="",
            func_name="get_stock_list",
            market=market,
        )
        return result or []

    async def get_industry_stocks(self, industry_code: str) -> List[str]:
        result, _ = await self._try_providers(
            operation="get_industry_stocks",
            data_type="industry_stocks",
            cache_key=industry_code,
            func_name="get_industry_stocks",
            industry_code=industry_code,
        )
        return result or []

    async def get_market_overview(self) -> dict:
        result, _ = await self._try_providers(
            operation="get_market_overview",
            data_type="market_overview",
            cache_key="",
            func_name="get_market_overview",
        )
        return result or {"data_source": "unavailable", "indices": {}}

    async def get_money_flow(self, symbol: str) -> dict:
        result, _ = await self._try_providers(
            operation="get_money_flow",
            data_type="money_flow",
            cache_key=symbol,
            func_name="get_money_flow",
            symbol=symbol,
        )
        return result or {"symbol": symbol, "data_source": "unavailable"}

    async def get_news(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        result, _ = await self._try_providers(
            operation="get_news",
            data_type="news",
            cache_key=symbol or "",
            func_name="get_news",
            symbol=symbol,
            limit=limit,
        )
        return result or []

    async def get_announcements(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        result, _ = await self._try_providers(
            operation="get_announcements",
            data_type="announcements",
            cache_key=symbol or "",
            func_name="get_announcements",
            symbol=symbol,
            limit=limit,
        )
        return result or []

    async def get_quote_with_availability(self, symbol: str) -> tuple:
        return await self._try_providers(
            operation="get_realtime_quote",
            data_type="quote",
            cache_key=symbol,
            func_name="get_realtime_quote",
            symbol=symbol,
        )

    async def get_kline_with_availability(
        self, symbol: str, timeframe: str = "D", limit: int = 100,
        start_date: Optional[str] = None, end_date: Optional[str] = None,
    ) -> tuple:
        cache_type = f"kline_{timeframe.lower()}"
        return await self._try_providers(
            operation="get_kline",
            data_type=cache_type,
            cache_key=symbol,
            func_name="get_kline",
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
