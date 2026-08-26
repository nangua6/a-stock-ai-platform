"""
Market Context Builder – converts market data into stable AI context.

All AI agents receive data through this builder. No raw DataFrames,
no missing fields defaulted to 0, no fabricated data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.market.base import (
    DataAvailability,
    DataFreshness,
    FinancialData,
    KlineData,
    QuoteData,
    StockAnalysisSnapshot,
    TechnicalIndicators,
)
from app.market.provider_manager import ProviderManager
from app.services.technical_analysis import TechnicalAnalysisService
from app.core.logging import get_logger

logger = get_logger("market_context")


UNAVAILABLE = "UNAVAILABLE"
NOT_AVAILABLE = "NOT_AVAILABLE"


class MarketContextBuilder:
    """
    Builds structured market context for AI agents.

    Rules:
    - Missing data is explicitly marked UNAVAILABLE
    - Never defaults missing fields to 0
    - Never fabricates data
    - Always includes data freshness/source/timestamp
    """

    def __init__(self, provider: ProviderManager):
        self.provider = provider
        self.ta_service = TechnicalAnalysisService()

    async def build_stock_snapshot(self, symbol: str) -> StockAnalysisSnapshot:
        """
        Build a full StockAnalysisSnapshot for a single stock.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Quote
        quote, quote_avail = await self.provider.get_quote_with_availability(symbol)

        # 2. Klines (60 bars for TA)
        klines, kline_avail = await self.provider.get_kline_with_availability(
            symbol, timeframe="D", limit=60,
        )

        # 3. Technical indicators
        technicals = None
        if klines and len(klines) >= 5:
            try:
                technicals = self.ta_service.compute(klines)
            except Exception as e:
                logger.warning("ta_compute_failed", symbol=symbol, error=str(e)[:100])

        # 4. Financials
        financials = None
        try:
            fin_data = await self.provider.get_financial_data(symbol)
            if fin_data and fin_data.data_source != "unavailable":
                financials = fin_data
        except Exception as e:
            logger.warning("financial_fetch_failed", symbol=symbol, error=str(e)[:100])

        # 5. Data quality assessment
        if quote and quote.price > 0:
            data_quality = quote_avail
        else:
            data_quality = DataAvailability(
                is_available=False,
                freshness=DataFreshness.UNAVAILABLE,
                provider="none",
                error_message="No quote data available",
            )

        # Build snapshot
        snapshot = StockAnalysisSnapshot(
            symbol=symbol,
            name=quote.name if quote and quote.name else UNAVAILABLE,
            market=symbol.split(".")[-1] if "." in symbol else UNAVAILABLE,
            current_price=quote.price if quote and quote.price > 0 else 0.0,
            change_pct=quote.change_pct if quote else 0.0,
            volume=quote.volume if quote else 0,
            amount=quote.amount if quote else 0.0,
            pre_close=quote.pre_close if quote else 0.0,
            klines=klines[-10:] if klines else [],
            technicals=technicals,
            financials=financials,
            volatility=technicals.volatility if technicals else 0.0,
            data_quality=data_quality,
            data_source=quote.data_source if quote else UNAVAILABLE,
            snapshot_time=now_iso,
        )

        return snapshot

    def snapshot_to_ai_context(self, snapshot: StockAnalysisSnapshot) -> Dict[str, Any]:
        """
        Convert a snapshot into a structured dict for AI prompts.
        Missing/unavailable data is explicitly marked.
        """
        ctx: Dict[str, Any] = {
            "symbol": snapshot.symbol,
            "name": snapshot.name,
            "market": snapshot.market,
            "snapshot_time": snapshot.snapshot_time,
            "data_source": snapshot.data_source,
        }

        # Quote section
        if snapshot.current_price > 0:
            ctx["quote"] = {
                "price": snapshot.current_price,
                "change_pct": snapshot.change_pct,
                "volume": snapshot.volume,
                "amount": snapshot.amount,
                "pre_close": snapshot.pre_close,
            }
        else:
            ctx["quote"] = UNAVAILABLE

        # Kline section
        if snapshot.klines:
            ctx["klines"] = [
                {
                    "date": k.trade_date,
                    "open": k.open,
                    "high": k.high,
                    "low": k.low,
                    "close": k.close,
                    "volume": k.volume,
                    "change_pct": k.change_pct,
                }
                for k in snapshot.klines
            ]
        else:
            ctx["klines"] = UNAVAILABLE

        # Technical indicators
        if snapshot.technicals:
            t = snapshot.technicals
            ctx["technicals"] = {
                "ma5": t.ma5,
                "ma10": t.ma10,
                "ma20": t.ma20,
                "ma60": t.ma60,
                "macd": {"line": t.macd_line, "signal": t.macd_signal, "histogram": t.macd_histogram},
                "rsi": t.rsi,
                "kdj": {"k": t.kdj_k, "d": t.kdj_d, "j": t.kdj_j},
                "bollinger": {"upper": t.boll_upper, "middle": t.boll_middle, "lower": t.boll_lower},
                "atr": t.atr,
                "vol_ma5": t.volume_ma5,
                "vol_ma10": t.volume_ma10,
                "volatility": t.volatility,
                "turnover_rate": t.turnover_rate,
                "bars_used": t.period,
            }
        else:
            ctx["technicals"] = UNAVAILABLE

        # Financials
        if snapshot.financials:
            f = snapshot.financials
            ctx["fundamentals"] = {
                "pe_ratio": f.pe_ratio if f.pe_ratio > 0 else NOT_AVAILABLE,
                "pb_ratio": f.pb_ratio if f.pb_ratio > 0 else NOT_AVAILABLE,
                "market_cap": f.market_cap if f.market_cap > 0 else NOT_AVAILABLE,
                "eps": f.eps if f.eps > 0 else NOT_AVAILABLE,
                "roe": f.roe if f.roe > 0 else NOT_AVAILABLE,
            }
        else:
            ctx["fundamentals"] = UNAVAILABLE

        # Data quality (always present)
        ctx["data_quality"] = snapshot.data_quality.to_dict()

        return ctx

    async def build_market_context(self) -> Dict[str, Any]:
        """Build market-level context (overview, indices)."""
        overview = await self.provider.get_market_overview()
        return {
            "market_overview": overview,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
