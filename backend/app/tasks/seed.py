"""
Database seed script – populates initial data for development.

Usage: python -m app.tasks.seed
"""
from __future__ import annotations

import asyncio

from app.core.database import get_db_context, init_db
from app.core.logging import setup_logging
from app.core.security import Role, hash_password
from app.market.mock_provider import MockMarketDataProvider
from app.repositories.factory import RepositoryFactory
from app.services.market_data_service import MarketDataService

# Default A-share stock universe for seeding
SEED_STOCKS = [
    {"symbol": "600519.SH", "name": "贵州茅台", "market": "SH", "industry": "白酒", "board": "MAIN"},
    {"symbol": "000858.SZ", "name": "五粮液", "market": "SZ", "industry": "白酒", "board": "MAIN"},
    {"symbol": "300750.SZ", "name": "宁德时代", "market": "SZ", "industry": "电池", "board": "GEM"},
    {"symbol": "600036.SH", "name": "招商银行", "market": "SH", "industry": "银行", "board": "MAIN"},
    {"symbol": "000001.SZ", "name": "平安银行", "market": "SZ", "industry": "银行", "board": "MAIN"},
    {"symbol": "601318.SH", "name": "中国平安", "market": "SH", "industry": "保险", "board": "MAIN"},
    {"symbol": "002475.SZ", "name": "立讯精密", "market": "SZ", "industry": "电子", "board": "GEM"},
    {"symbol": "600276.SH", "name": "恒瑞医药", "market": "SH", "industry": "医药", "board": "MAIN"},
    {"symbol": "601012.SH", "name": "隆基绿能", "market": "SH", "industry": "光伏", "board": "MAIN"},
    {"symbol": "002594.SZ", "name": "比亚迪", "market": "SZ", "industry": "汽车", "board": "GEM"},
    {"symbol": "600900.SH", "name": "长江电力", "market": "SH", "industry": "电力", "board": "MAIN"},
    {"symbol": "601899.SH", "name": "紫金矿业", "market": "SH", "industry": "有色金属", "board": "MAIN"},
    {"symbol": "600887.SH", "name": "伊利股份", "market": "SH", "industry": "食品饮料", "board": "MAIN"},
    {"symbol": "000333.SZ", "name": "美的集团", "market": "SZ", "industry": "家电", "board": "MAIN"},
    {"symbol": "002230.SZ", "name": "科大讯飞", "market": "SZ", "industry": "AI", "board": "GEM"},
    {"symbol": "688981.SH", "name": "中芯国际", "market": "SH", "industry": "半导体", "board": "STAR"},
    {"symbol": "603259.SH", "name": "药明康德", "market": "SH", "industry": "CXO", "board": "MAIN"},
    {"symbol": "300059.SZ", "name": "东方财富", "market": "SZ", "industry": "券商", "board": "GEM"},
    {"symbol": "002714.SZ", "name": "牧原股份", "market": "SZ", "industry": "养殖", "board": "GEM"},
    {"symbol": "600031.SH", "name": "三一重工", "market": "SH", "industry": "工程机械", "board": "MAIN"},
]


async def seed_database():
    """Seed the database with initial data."""
    setup_logging()
    from app.core.logging import get_logger
    logger = get_logger("seed")

    await init_db()

    async with get_db_context() as session:
        repos = RepositoryFactory(session)

        # 1. Create default admin user
        admin = await repos.users.find_one(username="admin")
        if not admin:
            admin = await repos.users.create({
                "username": "admin",
                "email": "admin@astock.local",
                "hashed_password": hash_password("admin123456"),
                "full_name": "系统管理员",
                "role": Role.ADMIN.value,
                "is_active": True,
            })
            logger.info("Created admin user", user_id=str(admin.id))
        else:
            logger.info("Admin user already exists")

        # 2. Create default paper account
        from app.services.account_service import AccountService
        account_svc = AccountService(session)
        account = await account_svc.get_default_paper_account(admin.id)
        logger.info("Default paper account ready", account_id=str(account.id))

        # 3. Seed stock list
        count = await repos.stocks.bulk_create(SEED_STOCKS)
        logger.info("Stock list seeded", new_count=count, total=len(SEED_STOCKS))

        # 4. Seed kline data using mock provider
        provider = MockMarketDataProvider()
        md_service = MarketDataService(session, provider)
        for stock in SEED_STOCKS[:5]:  # Top 5 stocks get kline data
            await md_service.sync_klines(stock["symbol"], limit=100)
        logger.info("Kline data seeded for top 5 stocks")

    logger.info("✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
