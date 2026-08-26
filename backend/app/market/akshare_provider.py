"""
AkShare market data provider.

Fetches real-time and historical A-share data via the AkShare library.
Data sourced from EastMoney, SSE, etc.  No API key required.

Resilience features:
- Per-request timeout
- Exponential backoff retry
- DNS / Connection / Timeout error handling
- Empty-data and format-change guards
- Structured error logging (no secrets)
- Proxy-aware: disables system proxy when it causes failures

NOTE: Requires network access. Use MockMarketDataProvider in sandbox/offline.
"""
from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import List, Optional

from app.core.logging import get_data_logger
from app.market.base import (
    FinancialData,
    KlineData,
    MarketDataProvider,
    QuoteData,
)

logger = get_data_logger()

# ── Retry configuration ──────────────────────────────────────────────────────
MAX_RETRIES = 3
BASE_DELAY = 1.0        # seconds
MAX_DELAY = 10.0        # seconds
REQUEST_TIMEOUT = 15.0  # seconds per akshare call


# ── Symbol format helpers ────────────────────────────────────────────────────
def _to_akshare_symbol(symbol: str) -> str:
    """600519.SH -> 600519"""
    return symbol.split(".")[0]


def _from_em_symbol(code: str, market: str) -> str:
    """600519, SH -> 600519.SH"""
    return f"{code}.{market}"


def _ensure_no_system_proxy():
    """
    Ensure that system proxy settings don't interfere with AkShare.

    On macOS with Clash/ClashX in TUN mode, Python's requests library picks up
    system proxy settings from networksetup. When the proxy is unstable for
    certain Eastmoney domains, we need to bypass it.

    This sets NO_PROXY=* which tells requests to not use any proxy.
    Direct connections work because Clash TUN mode still captures the traffic
    at the network level (transparent proxy).
    """
    if "NO_PROXY" not in os.environ and "no_proxy" not in os.environ:
        os.environ["NO_PROXY"] = "*"


# Initialize proxy bypass on module load
_ensure_no_system_proxy()


async def _retry_call(coro_factory, operation: str, symbol: str = ""):
    """
    Retry an async call with exponential backoff.

    coro_factory must be a callable returning a new coroutine each time.
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        start = time.time()
        try:
            result = await asyncio.wait_for(coro_factory(), timeout=REQUEST_TIMEOUT)
            elapsed = time.time() - start
            logger.info(
                "akshare_call_ok",
                operation=operation,
                symbol=symbol,
                attempt=attempt + 1,
                latency_ms=round(elapsed * 1000, 1),
            )
            return result
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            last_error = f"Timeout after {elapsed:.1f}s"
            logger.warning(
                "akshare_timeout",
                operation=operation,
                symbol=symbol,
                attempt=attempt + 1,
                latency_ms=round(elapsed * 1000, 1),
            )
        except ConnectionError as e:
            elapsed = time.time() - start
            last_error = f"ConnectionError: {e}"
            logger.warning(
                "akshare_connection_error",
                operation=operation,
                symbol=symbol,
                attempt=attempt + 1,
                error=str(e)[:200],
            )
        except OSError as e:
            elapsed = time.time() - start
            last_error = f"OSError({e.errno}): {e}"
            logger.warning(
                "akshare_network_error",
                operation=operation,
                symbol=symbol,
                attempt=attempt + 1,
                error=str(e)[:200],
            )
        except Exception as e:
            elapsed = time.time() - start
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(
                "akshare_unexpected_error",
                operation=operation,
                symbol=symbol,
                attempt=attempt + 1,
                error_type=type(e).__name__,
                error=str(e)[:200],
            )

        # Exponential backoff (skip on last attempt)
        if attempt < MAX_RETRIES - 1:
            delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
            await asyncio.sleep(delay)

    # All retries exhausted
    raise ConnectionError(f"AkShare {operation} failed after {MAX_RETRIES} retries: {last_error}")


class AkShareProvider(MarketDataProvider):
    """
    AkShare-based market data provider with resilience.

    All external calls go through retry logic with timeout and backoff.
    Empty data returns are explicitly handled (never silently ignored).
    """

    def __init__(self, cache_ttl_seconds: int = 60):
        self._cache_ttl = cache_ttl_seconds
        self._quote_cache: dict = {}  # symbol -> (QuoteData, timestamp)

    @property
    def name(self) -> str:
        return "akshare"

    async def get_realtime_quote(self, symbol: str) -> QuoteData:
        """Get real-time quote via akshare (东方财富)."""
        # Check local cache
        cached = self._quote_cache.get(symbol)
        if cached and (time.time() - cached[1]) < self._cache_ttl:
            return cached[0]

        import akshare as ak

        ak_symbol = _to_akshare_symbol(symbol)

        async def _fetch():
            return await asyncio.to_thread(ak.stock_individual_info_em, ak_symbol)

        df = await _retry_call(_fetch, operation="get_realtime_quote", symbol=symbol)

        if df is None or df.empty:
            raise ValueError(f"AkShare returned empty data for {symbol}")

        try:
            info = dict(zip(df["item"], df["value"]))
        except (KeyError, TypeError) as e:
            raise ValueError(f"AkShare format change for {symbol}: {e}")

        price = float(info.get("最新价", 0) or 0)
        pre_close = float(info.get("昨收", 0) or 0)
        change = round(price - pre_close, 2) if pre_close else 0
        change_pct = round(change / pre_close * 100, 2) if pre_close else 0

        quote = QuoteData(
            symbol=symbol,
            name=str(info.get("股票简称", "")),
            price=price,
            open=float(info.get("今开", 0) or 0),
            high=price,
            low=price,
            pre_close=pre_close,
            volume=int(info.get("成交量", 0) or 0),
            amount=float(info.get("成交额", 0) or 0),
            change=change,
            change_pct=change_pct,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data_source="akshare",
        )
        self._quote_cache[symbol] = (quote, time.time())
        return quote

    async def get_realtime_quotes(self, symbols: List[str]) -> List[QuoteData]:
        """Batch get quotes (sequential to respect rate limits)."""
        results = []
        for sym in symbols:
            try:
                q = await self.get_realtime_quote(sym)
                results.append(q)
            except Exception as e:
                logger.warning("akshare_batch_quote_skip", symbol=sym, error=str(e)[:100])
                continue
        if not results and symbols:
            raise ConnectionError("AkShare batch quote: all symbols failed")
        return results

    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "D",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[KlineData]:
        """Get historical K-line data via akshare."""
        import akshare as ak

        ak_symbol = _to_akshare_symbol(symbol)
        period_map = {"D": "daily", "W": "weekly", "M": "monthly"}
        period = period_map.get(timeframe, "daily")
        sd = start_date.replace("-", "") if start_date else "20250101"
        ed = end_date.replace("-", "") if end_date else datetime.now().strftime("%Y%m%d")

        async def _fetch():
            return await asyncio.to_thread(
                ak.stock_zh_a_hist,
                symbol=ak_symbol,
                period=period,
                start_date=sd,
                end_date=ed,
                adjust="qfq",
            )

        df = await _retry_call(_fetch, operation="get_kline", symbol=symbol)

        if df is None or df.empty:
            logger.warning("akshare_empty_kline", symbol=symbol, timeframe=timeframe)
            return []

        bars = []
        for _, row in df.tail(limit).iterrows():
            try:
                bars.append(KlineData(
                    symbol=symbol,
                    trade_date=str(row.get("日期", "")),
                    timeframe=timeframe,
                    open=float(row.get("开盘", 0)),
                    high=float(row.get("最高", 0)),
                    low=float(row.get("最低", 0)),
                    close=float(row.get("收盘", 0)),
                    volume=int(row.get("成交量", 0)),
                    amount=float(row.get("成交额", 0)),
                    change_pct=float(row.get("涨跌幅", 0)),
                    turnover=float(row.get("换手率", 0) or 0),
                    data_source="akshare",
                    available_time=datetime.now(timezone.utc).isoformat(),
                ))
            except (ValueError, TypeError) as e:
                logger.warning("akshare_kline_parse_error", symbol=symbol, error=str(e)[:100])
                continue

        if not bars:
            raise ValueError(f"AkShare kline parse produced 0 bars for {symbol}")

        return bars

    async def get_financial_data(self, symbol: str) -> FinancialData:
        """Get financial data via akshare."""
        import akshare as ak

        ak_symbol = _to_akshare_symbol(symbol)

        async def _fetch():
            return await asyncio.to_thread(ak.stock_individual_info_em, ak_symbol)

        df = await _retry_call(_fetch, operation="get_financial_data", symbol=symbol)

        if df is None or df.empty:
            raise ValueError(f"AkShare empty financial data for {symbol}")

        info = dict(zip(df["item"], df["value"]))

        return FinancialData(
            symbol=symbol,
            report_date=datetime.now().strftime("%Y-%m-%d"),
            pe_ratio=float(info.get("市盈率(动态)", 0) or 0),
            pb_ratio=float(info.get("市净率", 0) or 0),
            market_cap=float(info.get("总市值", 0) or 0),
            total_share=float(info.get("总股本", 0) or 0),
            data_source="akshare",
        )

    async def get_stock_list(self, market: Optional[str] = None) -> List[dict]:
        """Get all A-share stock list."""
        import akshare as ak

        async def _fetch():
            return await asyncio.to_thread(ak.stock_zh_a_spot_em)

        df = await _retry_call(_fetch, operation="get_stock_list")

        if df is None or df.empty:
            raise ValueError("AkShare returned empty stock list")

        results = []
        for _, row in df.iterrows():
            try:
                code = str(row.get("代码", ""))
                if len(code) != 6:
                    continue
                mkt = "SH" if code.startswith("6") else "SZ"
                if market and mkt != market:
                    continue
                results.append({
                    "symbol": f"{code}.{mkt}",
                    "name": str(row.get("名称", "")),
                    "market": mkt,
                })
            except Exception:
                continue
        return results

    async def get_industry_stocks(self, industry_code: str) -> List[str]:
        """Get stocks in an industry sector."""
        import akshare as ak

        async def _fetch():
            return await asyncio.to_thread(ak.stock_board_industry_cons_em, industry_code)

        df = await _retry_call(_fetch, operation="get_industry_stocks", symbol=industry_code)

        if df is None or df.empty:
            return []
        return [str(row["代码"]) for _, row in df.iterrows()]

    async def get_market_overview(self) -> dict:
        """Get market overview from major indices."""
        import akshare as ak

        indices = {}
        index_map = {
            "上证指数": "sh000001",
            "深证成指": "sz399001",
            "创业板指": "sz399006",
            "科创50": "sh000688",
        }

        for name, code in index_map.items():
            try:
                async def _fetch(c=code):
                    return await asyncio.to_thread(ak.stock_zh_index_daily_em, c)

                df = await _retry_call(_fetch, operation="get_index", symbol=code)
                if df is not None and not df.empty:
                    last = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else last
                    close = float(last.get("close", 0))
                    prev_close = float(prev.get("close", 1))
                    change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close else 0
                    indices[name] = {"price": close, "change_pct": change_pct}
            except Exception as e:
                logger.warning("akshare_index_failed", index=name, error=str(e)[:100])
                continue

        if not indices:
            raise ConnectionError("AkShare market overview: all indices failed")

        return {
            "indices": indices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "akshare",
        }

    async def get_money_flow(self, symbol: str) -> dict:
        """Get capital flow data."""
        import akshare as ak

        ak_symbol = _to_akshare_symbol(symbol)

        async def _fetch():
            return await asyncio.to_thread(ak.stock_individual_fund_flow, ak_symbol)

        df = await _retry_call(_fetch, operation="get_money_flow", symbol=symbol)

        if df is None or df.empty:
            return {"symbol": symbol, "data_source": "akshare"}

        last = df.iloc[-1]
        return {
            "symbol": symbol,
            "main_net_inflow": float(last.get("主力净流入-净额", 0) or 0),
            "retail_net_inflow": float(last.get("小单净流入-净额", 0) or 0),
            "data_source": "akshare",
        }

    async def get_news(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        """Get recent financial news."""
        import akshare as ak

        ak_symbol = _to_akshare_symbol(symbol) if symbol else "000001"

        async def _fetch():
            return await asyncio.to_thread(ak.stock_news_em, ak_symbol)

        df = await _retry_call(_fetch, operation="get_news", symbol=ak_symbol)

        if df is None or df.empty:
            return []

        results = []
        for _, row in df.head(limit).iterrows():
            results.append({
                "title": str(row.get("新闻标题", "")),
                "source": str(row.get("新闻来源", "")),
                "time": str(row.get("发布时间", "")),
                "url": str(row.get("新闻链接", "")),
            })
        return results

    async def get_announcements(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        """Get recent company announcements."""
        import akshare as ak

        if not symbol:
            return []

        ak_symbol = _to_akshare_symbol(symbol)

        async def _fetch():
            return await asyncio.to_thread(ak.stock_report_fund_hold_detail, ak_symbol)

        df = await _retry_call(_fetch, operation="get_announcements", symbol=symbol)

        if df is None or df.empty:
            return []

        return [
            {"title": str(row.get("公告", "")), "time": str(row.get("日期", ""))}
            for _, row in df.head(limit).iterrows()
        ]
