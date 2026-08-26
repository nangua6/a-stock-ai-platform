"""Mock market data provider for development and testing."""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import List, Optional

from app.market.base import (
    FinancialData,
    KlineData,
    MarketDataProvider,
    QuoteData,
)

# Seed data for some well-known A-share stocks
MOCK_STOCKS = {
    "600519.SH": {"name": "贵州茅台", "industry": "白酒", "base_price": 1450.0},
    "000858.SZ": {"name": "五粮液", "industry": "白酒", "base_price": 120.0},
    "300750.SZ": {"name": "宁德时代", "industry": "电池", "base_price": 180.0},
    "600036.SH": {"name": "招商银行", "industry": "银行", "base_price": 38.0},
    "000001.SZ": {"name": "平安银行", "industry": "银行", "base_price": 12.5},
    "601318.SH": {"name": "中国平安", "industry": "保险", "base_price": 45.0},
    "002475.SZ": {"name": "立讯精密", "industry": "电子", "base_price": 32.0},
    "600276.SH": {"name": "恒瑞医药", "industry": "医药", "base_price": 42.0},
    "601012.SH": {"name": "隆基绿能", "industry": "光伏", "base_price": 22.0},
    "002594.SZ": {"name": "比亚迪", "industry": "汽车", "base_price": 220.0},
}


class MockMarketDataProvider(MarketDataProvider):
    """Mock provider with randomized but realistic data for dev/testing."""

    @property
    def name(self) -> str:
        return "mock"

    async def get_realtime_quote(self, symbol: str) -> QuoteData:
        info = MOCK_STOCKS.get(symbol, {"name": symbol, "industry": "未知", "base_price": 50.0})
        base = info["base_price"]
        noise = random.uniform(-0.03, 0.03)
        price = round(base * (1 + noise), 2)
        pre_close = round(base * (1 + random.uniform(-0.01, 0.01)), 2)
        change = round(price - pre_close, 2)
        change_pct = round(change / pre_close * 100, 2) if pre_close else 0
        return QuoteData(
            symbol=symbol,
            name=info["name"],
            price=price,
            open=round(pre_close * (1 + random.uniform(-0.005, 0.005)), 2),
            high=round(price * (1 + random.uniform(0, 0.02)), 2),
            low=round(price * (1 - random.uniform(0, 0.02)), 2),
            pre_close=pre_close,
            volume=random.randint(50_000, 5_000_000),
            amount=round(random.uniform(1e8, 5e9), 2),
            change=change,
            change_pct=change_pct,
            bid1_price=round(price * 0.999, 2),
            ask1_price=round(price * 1.001, 2),
            bid1_volume=random.randint(100, 10000),
            ask1_volume=random.randint(100, 10000),
            timestamp=datetime.now(timezone.utc).isoformat(),
            data_source="mock",
        )

    async def get_realtime_quotes(self, symbols: List[str]) -> List[QuoteData]:
        return [await self.get_realtime_quote(s) for s in symbols]

    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "D",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[KlineData]:
        info = MOCK_STOCKS.get(symbol, {"base_price": 50.0})
        base = info["base_price"]
        bars = []
        price = base
        for i in range(limit, 0, -1):
            change = random.uniform(-0.04, 0.04)
            o = round(price, 2)
            c = round(price * (1 + change), 2)
            h = round(max(o, c) * (1 + random.uniform(0, 0.02)), 2)
            l = round(min(o, c) * (1 - random.uniform(0, 0.02)), 2)
            v = random.randint(100_000, 10_000_000)
            bars.append(KlineData(
                symbol=symbol,
                trade_date=f"2026-{8 - (i // 30):02d}-{(30 - i % 30):02d}",
                timeframe=timeframe,
                open=o, high=h, low=l, close=c,
                volume=v,
                amount=round(c * v, 2),
                change_pct=round(change * 100, 2),
                data_source="mock",
                available_time=datetime.now(timezone.utc).isoformat(),
            ))
            price = c
        return bars

    async def get_financial_data(self, symbol: str) -> FinancialData:
        info = MOCK_STOCKS.get(symbol, {"base_price": 50.0})
        return FinancialData(
            symbol=symbol,
            report_date="2026-06-30",
            revenue=round(random.uniform(1e9, 1e12), 2),
            net_profit=round(random.uniform(1e8, 1e11), 2),
            eps=round(random.uniform(0.5, 20.0), 2),
            roe=round(random.uniform(5, 30), 2),
            pe_ratio=round(random.uniform(10, 60), 2),
            pb_ratio=round(random.uniform(1, 15), 2),
            market_cap=round(random.uniform(1e10, 2e12), 2),
            total_share=round(random.uniform(1e8, 1e11), 0),
            data_source="mock",
        )

    async def get_stock_list(self, market: Optional[str] = None) -> List[dict]:
        return [
            {"symbol": sym, "name": info["name"], "industry": info["industry"], "market": sym.split(".")[-1]}
            for sym, info in MOCK_STOCKS.items()
            if market is None or sym.endswith(f".{market}")
        ]

    async def get_industry_stocks(self, industry_code: str) -> List[str]:
        return [sym for sym, info in MOCK_STOCKS.items() if info["industry"] == industry_code]

    async def get_market_overview(self) -> dict:
        return {
            "indices": {
                "上证指数": {"price": 3250 + random.uniform(-30, 30), "change_pct": random.uniform(-1, 1)},
                "深证成指": {"price": 10500 + random.uniform(-100, 100), "change_pct": random.uniform(-1.5, 1.5)},
                "创业板指": {"price": 2100 + random.uniform(-30, 30), "change_pct": random.uniform(-2, 2)},
                "科创50": {"price": 980 + random.uniform(-15, 15), "change_pct": random.uniform(-2, 2)},
            },
            "up_count": random.randint(1000, 3500),
            "down_count": random.randint(800, 3000),
            "limit_up_count": random.randint(0, 50),
            "limit_down_count": random.randint(0, 20),
            "total_amount": round(random.uniform(6e11, 1.5e12), 2),
            "northbound_flow": round(random.uniform(-5e10, 5e10), 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "mock",
        }

    async def get_money_flow(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "main_net_inflow": round(random.uniform(-1e9, 1e9), 2),
            "retail_net_inflow": round(random.uniform(-5e8, 5e8), 2),
            "northbound_net_inflow": round(random.uniform(-1e8, 1e8), 2),
            "data_source": "mock",
        }

    async def get_news(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        return [
            {"title": f"[Mock] {symbol or 'A股'} 重大新闻 #{i+1}", "source": "模拟新闻", "time": "2026-08-25 09:00", "url": ""}
            for i in range(min(limit, 5))
        ]

    async def get_announcements(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        return [
            {"title": f"[Mock] {symbol or 'A股'} 公告 #{i+1}", "type": "日常公告", "time": "2026-08-25", "url": ""}
            for i in range(min(limit, 3))
        ]
