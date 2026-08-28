"""
Market data provider factory.

Creates the correct provider chain based on MARKET_DATA_MODE setting.

Modes:
- mock: MockMarketDataProvider (for unit tests)
- real: AkShareProvider with MockMarketDataProvider fallback

Fallback behavior:
- In real mode, if AkShare fails → fallback to Mock with explicit fallback_reason
- The fallback_reason is recorded in every response
- This prevents "silently using mock data" in production
"""
from __future__ import annotations

from typing import Optional

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.market.cache import MarketDataCache
from app.market.mock_provider import MockMarketDataProvider
from app.market.provider_manager import ProviderManager

logger = get_logger("market.factory")


def _get_market_data_mode() -> str:
    """Get the current market data mode string ('mock' or 'real')."""
    settings = get_settings()
    return settings.market_data_mode.value


def create_provider(mode: Optional[str] = None, cache: Optional[MarketDataCache] = None):
    """
    Create a market data provider based on mode.

    Returns a MarketDataProvider (usually ProviderManager).
    """
    settings = get_settings()
    effective_mode = mode or settings.market_data_mode.value
    cache = cache or MarketDataCache()

    if effective_mode == "mock":
        logger.info("Creating MOCK market data provider")
        return ProviderManager(
            providers=[MockMarketDataProvider()],
            cache=cache,
        )

    # Real mode: try AkShare first, fallback to Mock
    try:
        from app.market.akshare_provider import AkShareProvider
        akshare = AkShareProvider()
        logger.info("Creating REAL market data provider (AkShare + Mock fallback)")
        return ProviderManager(
            providers=[akshare, MockMarketDataProvider()],
            cache=cache,
        )
    except ImportError:
        logger.warning("AkShare not available, falling back to mock with reason=akshare_import_failed")
        return ProviderManager(
            providers=[MockMarketDataProvider()],
            cache=cache,
        )
    except Exception as e:
        logger.warning("AkShare init failed, falling back to mock", error=str(e))
        return ProviderManager(
            providers=[MockMarketDataProvider()],
            cache=cache,
        )


def create_llm_provider(mode: Optional[str] = None):
    """
    Create an LLM provider based on mode.

    Returns an LLMProvider.
    """
    from app.ai.client import get_llm_provider
    return get_llm_provider(mode=mode)
