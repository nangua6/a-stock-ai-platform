"""
AkShare market data provider.

Fetches real-time and historical A-share data via the AkShare library.
Data sourced from EastMoney, SSE, etc.  No API key required.

Resilience features:
- Per-request timeout (15s)
- Exponential backoff retry (3 attempts)
- DNS / Connection / Timeout error handling
- Empty-data and format-change guards
- Structured error logging (no secrets)

NOTE: Requires network access. Use MockMarketDataProvider in sandbox/offline.
"""
from __future__ import annotations

import asyncio
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
BASE_DELAY = 1.0
MAX_DELAY = 10.0
REQUEST_TIMEOUT = 15.0


def _to_akshare_symbol(symbol: str) -> str:
    """600519.SH -> 600519"""
    return symbol.split(".")[0]


async def _retry_call(coro_factory, operation: str, symbol: str = ""):
    """Retry an async call with exponential backoff."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        start = time.time()
        try:
            result = await asyncio.wait_for(coro_factory(), timeout=REQUEST_TIMEOUT)
            elapsed = time.time() - start
            logger.info(
                "akshare_call_ok", operation=operation, symbol=symbol,
                attempt=attempt + 1, latency_ms=round(elapsed * 1000, 1),
            )
            return result
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            last_error = f"Timeout after {elapsed:.1f}s"
            logger.warning(
                "akshare_timeout", operation=operation, symbol=symbol,
                attempt=attempt + 1, latency_ms=round(elapsed * 1000, 1),
            )
        except ConnectionError as e:
            elapsed = time.time() - start
            last_error = f"ConnectionError: {e}"
            logger.warning(
                "akshare_connection_error", operation=operation, symbol=symbol,
                attempt=attempt + 1, error=str(e)[:200],
            )
        except OSError as e:
            elapsed = time.time() - start
            last_error = f"OSError({e.errno}): {e}"
            logger.warning(
                "akshare_network_error", operation=operation, symbol=symbol,
                attempt=attempt + 1, error=str(e)[:200],
            )
        except Exception as e:
            elapsed = time.time() - start
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(
                "akshare_unexpected_error", operation=operation, symbol=symbol,
                attempt=attempt + 1, error_type=type(e).__name__, error=str(e)[:200],
            )
        if attempt < MAX_RETRIES - 1:
            delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
            await asyncio.sleep(delay)
    raise ConnectionError(f"AkShare {operation} failed after {MAX_RETRIES} retries: {last_error}")


class AkShareProvider(MarketDataProvider):
    """AkShare-based market data provider with resilience."""

    def __init__(self, cache_ttl_seconds: int = 60):
        self._cache_ttl = cache_ttl_seconds
        self._quote_cache: dict = {}

    @property
    def name(self) -> str:
        return "akshare"

    async def get_realtime_quote(self, symbol: str) -> QuoteData:
        """Get real-time quote. Uses stock_individual_info_em + latest kline bar."""
        cached = self._quote_cache.get(symbol)
        if cached and (time.time() - cached[1]) < self._cache_ttl:
            return cached[0]

        import akshare as ak
        ak_symbol = _to_akshare_symbol(symbol)

        async def _fetch_info():
            return await asyncio.to_thread(ak.stock_individual_info_em, ak_symbol)

        df = await _retry_call(_fetch_info, operation="get_realtime_quote", symbol=symbol)
        if df is None or df.empty:
            raise ValueError(f"AkShare returned empty data for {symbol}")

        try:
            info = dict(zip(df["item"], df["value"]))
        except (KeyError, TypeError) as e:
            raise ValueError(f"AkShare format change for {symbol}: {e}")

        price = float(info.get("最新", 0) or 0)

        # Enrich with kline data (optional – failure is non-fatal)
        volume = 0; amount = 0.0; change_pct = 0.0; pre_close = 0.0
        open_price = 0.0; high = 0.0; low = 0.0
        try:
            kdf = await asyncio.wait_for(
                asyncio.to_thread(
                    ak.stock_zh_a_hist, symbol=ak_symbol, period="daily",
                    start_date="20260101", end_date=datetime.now().strftime("%Y%m%d"),
                    adjust="qfq",
                ), timeout=10,
            )
            if kdf is not None and not kdf.empty:
                last = kdf.iloc[-1]
                volume = int(last.get("成交量", 0) or 0)
                amount = float(last.get("成交额", 0) or 0)
                change_pct = float(last.get("涨跌幅", 0) or 0)
                open_price = float(last.get("开盘", 0) or 0)
                high = float(last.get("最高", 0) or 0)
                low = float(last.get("最低", 0) or 0)
                if len(kdf) >= 2:
                    pre_close = float(kdf.iloc[-2].get("收盘", 0) or 0)
        except Exception:
            pass

        quote = QuoteData(
            symbol=symbol, name=str(info.get("股票简称", "")),
            price=price, open=open_price, high=high, low=low,
            pre_close=pre_close, volume=volume, amount=amount,
            change=round(price - pre_close, 2) if pre_close else 0,
            change_pct=change_pct,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data_source="akshare",
        )
        self._quote_cache[symbol] = (quote, time.time())
        return quote

    async def get_realtime_quotes(self, symbols: List[str]) -> List[QuoteData]:
        results = []
        for sym in symbols:
            try:
                results.append(await self.get_realtime_quote(sym))
            except Exception as e:
                logger.warning("akshare_batch_quote_skip", symbol=sym, error=str(e)[:100])
        if not results and symbols:
            raise ConnectionError("AkShare batch quote: all symbols failed")
        return results

    async def get_kline(self, symbol: str, timeframe: str = "D",
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        limit: int = 100) -> List[KlineData]:
        import akshare as ak
        ak_symbol = _to_akshare_symbol(symbol)
        period_map = {"D": "daily", "W": "weekly", "M": "monthly"}
        period = period_map.get(timeframe, "daily")
        sd = start_date.replace("-", "") if start_date else "20250101"
        ed = end_date.replace("-", "") if end_date else datetime.now().strftime("%Y%m%d")

        async def _fetch():
            return await asyncio.to_thread(
                ak.stock_zh_a_hist, symbol=ak_symbol, period=period,
                start_date=sd, end_date=ed, adjust="qfq",
            )

        df = await _retry_call(_fetch, operation="get_kline", symbol=symbol)
        if df is None or df.empty:
            return []

        bars = []
        for _, row in df.tail(limit).iterrows():
            try:
                bars.append(KlineData(
                    symbol=symbol, trade_date=str(row.get("日期", "")),
                    timeframe=timeframe,
                    open=float(row.get("开盘", 0)), high=float(row.get("最高", 0)),
                    low=float(row.get("最低", 0)), close=float(row.get("收盘", 0)),
                    volume=int(row.get("成交量", 0)), amount=float(row.get("成交额", 0)),
                    change_pct=float(row.get("涨跌幅", 0)),
                    turnover=float(row.get("换手率", 0) or 0),
                    data_source="akshare",
                    available_time=datetime.now(timezone.utc).isoformat(),
                ))
            except (ValueError, TypeError) as e:
                logger.warning("akshare_kline_parse_error", symbol=symbol, error=str(e)[:100])
        if not bars:
            raise ValueError(f"AkShare kline parse produced 0 bars for {symbol}")
        return bars

    async def get_financial_data(self, symbol: str) -> FinancialData:
        import akshare as ak
        ak_symbol = _to_akshare_symbol(symbol)

        async def _fetch():
            return await asyncio.to_thread(ak.stock_individual_info_em, ak_symbol)

        df = await _retry_call(_fetch, operation="get_financial_data", symbol=symbol)
        if df is None or df.empty:
            raise ValueError(f"AkShare empty financial data for {symbol}")
        info = dict(zip(df["item"], df["value"]))
        return FinancialData(
            symbol=symbol, report_date=datetime.now().strftime("%Y-%m-%d"),
            pe_ratio=float(info.get("市盈率(动态)", 0) or 0),
            pb_ratio=float(info.get("市净率", 0) or 0),
            market_cap=float(info.get("总市值", 0) or 0),
            total_share=float(info.get("总股本", 0) or 0),
            data_source="akshare",
        )

    async def get_stock_list(self, market: Optional[str] = None) -> List[dict]:
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
                results.append({"symbol": f"{code}.{mkt}", "name": str(row.get("名称", "")), "market": mkt})
            except Exception:
                continue
        return results

    async def get_industry_stocks(self, industry_code: str) -> List[str]:
        import akshare as ak

        async def _fetch():
            return await asyncio.to_thread(ak.stock_board_industry_cons_em, industry_code)

        df = await _retry_call(_fetch, operation="get_industry_stocks", symbol=industry_code)
        if df is None or df.empty:
            return []
        return [str(row["代码"]) for _, row in df.iterrows()]

    async def get_market_overview(self) -> dict:
        import akshare as ak
        indices = {}
        for name, code in [("上证指数", "sh000001"), ("深证成指", "sz399001"),
                           ("创业板指", "sz399006"), ("科创50", "sh000688")]:
            try:
                async def _fetch(c=code):
                    return await asyncio.to_thread(ak.stock_zh_index_daily_em, c)
                df = await _retry_call(_fetch, operation="get_index", symbol=code)
                if df is not None and not df.empty:
                    last = df.iloc[-1]; prev = df.iloc[-2] if len(df) > 1 else last
                    close = float(last.get("close", 0)); prev_close = float(prev.get("close", 1))
                    chg = round((close - prev_close) / prev_close * 100, 2) if prev_close else 0
                    indices[name] = {"price": close, "change_pct": chg}
            except Exception as e:
                logger.warning("akshare_index_failed", index=name, error=str(e)[:100])
        if not indices:
            raise ConnectionError("AkShare market overview: all indices failed")
        return {"indices": indices, "timestamp": datetime.now(timezone.utc).isoformat(), "data_source": "akshare"}

    async def get_money_flow(self, symbol: str) -> dict:
        import akshare as ak
        ak_symbol = _to_akshare_symbol(symbol)

        async def _fetch():
            return await asyncio.to_thread(ak.stock_individual_fund_flow, ak_symbol)

        df = await _retry_call(_fetch, operation="get_money_flow", symbol=symbol)
        if df is None or df.empty:
            return {"symbol": symbol, "data_source": "akshare"}
        last = df.iloc[-1]
        return {"symbol": symbol, "main_net_inflow": float(last.get("主力净流入-净额", 0) or 0),
                "retail_net_inflow": float(last.get("小单净流入-净额", 0) or 0), "data_source": "akshare"}

    async def get_news(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        import akshare as ak
        ak_symbol = _to_akshare_symbol(symbol) if symbol else "000001"

        async def _fetch():
            return await asyncio.to_thread(ak.stock_news_em, ak_symbol)

        df = await _retry_call(_fetch, operation="get_news", symbol=ak_symbol)
        if df is None or df.empty:
            return []
        return [{"title": str(row.get("新闻标题", "")), "source": str(row.get("新闻来源", "")),
                 "time": str(row.get("发布时间", "")), "url": str(row.get("新闻链接", ""))}
                for _, row in df.head(limit).iterrows()]

    async def get_announcements(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        import akshare as ak
        if not symbol:
            return []
        ak_symbol = _to_akshare_symbol(symbol)

        async def _fetch():
            return await asyncio.to_thread(ak.stock_report_fund_hold_detail, ak_symbol)

        df = await _retry_call(_fetch, operation="get_announcements", symbol=symbol)
        if df is None or df.empty:
            return []
        return [{"title": str(row.get("公告", "")), "time": str(row.get("日期", ""))}
                for _, row in df.head(limit).iterrows()]
