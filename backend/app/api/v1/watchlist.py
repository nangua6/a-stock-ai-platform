"""
Watchlist endpoints – CRUD for user's tracked stocks.

Uses a default development user when no auth is present.
The user_id abstraction allows future auth integration without API changes.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.market.provider_manager import ProviderManager
from app.market.mock_provider import MockMarketDataProvider
from app.market.cache import MarketDataCache

router = APIRouter()

# Default user ID for development (no auth)
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

_provider = ProviderManager(providers=[MockMarketDataProvider()], cache=MarketDataCache())


class WatchlistAddRequest(BaseModel):
    symbol: str
    name: str = ""


def _get_user_id() -> uuid.UUID:
    """Get current user ID. Replace with real auth when available."""
    return DEFAULT_USER_ID


@router.get("")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Get all watchlist items with latest quotes."""
    from app.repositories.factory import RepositoryFactory
    repos = RepositoryFactory(db)
    user_id = _get_user_id()

    items = await repos.watchlist.get_by_user(user_id)

    # Enrich with live quotes
    enriched = []
    for item in items:
        quote_data = None
        try:
            quote = await _provider.get_realtime_quote(item.symbol)
            quote_data = {
                "price": quote.price,
                "change_pct": quote.change_pct,
                "volume": quote.volume,
                "amount": quote.amount,
                "timestamp": quote.timestamp,
                "data_source": quote.data_source,
            }
        except Exception:
            quote_data = None

        enriched.append({
            "id": str(item.id),
            "symbol": item.symbol,
            "name": item.name,
            "note": item.note,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "quote": quote_data,
        })

    return {"success": True, "data": enriched}


@router.post("")
async def add_to_watchlist(
    request: WatchlistAddRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a stock to watchlist. Idempotent."""
    from app.repositories.factory import RepositoryFactory
    repos = RepositoryFactory(db)
    user_id = _get_user_id()

    # Normalize symbol
    symbol = request.symbol.strip().upper()

    # Try to get name from provider if not provided
    name = request.name
    if not name:
        try:
            quote = await _provider.get_realtime_quote(symbol)
            name = quote.name
        except Exception:
            name = symbol

    item = await repos.watchlist.add_item(user_id, symbol, name)
    return {
        "success": True,
        "data": {
            "id": str(item.id),
            "symbol": item.symbol,
            "name": item.name,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        },
    }


@router.delete("/{symbol}")
async def remove_from_watchlist(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a stock from watchlist."""
    from app.repositories.factory import RepositoryFactory
    repos = RepositoryFactory(db)
    user_id = _get_user_id()

    removed = await repos.watchlist.remove_item(user_id, symbol.strip().upper())
    if not removed:
        raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
    return {"success": True, "data": {"symbol": symbol, "removed": True}}


@router.get("/{symbol}/check")
async def check_watchlist(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if a stock is in watchlist."""
    from app.repositories.factory import RepositoryFactory
    repos = RepositoryFactory(db)
    user_id = _get_user_id()

    exists = await repos.watchlist.is_in_watchlist(user_id, symbol.strip().upper())
    return {"success": True, "data": {"symbol": symbol, "in_watchlist": exists}}
