"""Real integration test for AnnouncementTool with AkShare.

Run on macOS with real network access:
    cd backend && source .venv/bin/activate
    HTTP_PROXY='' HTTPS_PROXY='' ALL_PROXY='' NO_PROXY='*' \
    pytest tests/integration/test_real_announcements.py -v -m integration
"""
import pytest


@pytest.mark.integration
class TestRealAnnouncementProvider:
    """Test AkShareAnnouncementProvider with real AkShare API."""

    @pytest.mark.asyncio
    async def test_get_announcements_600519(self):
        """Fetch real announcements for 600519.SH (贵州茅台)."""
        from app.announcements.provider import AkShareAnnouncementProvider
        provider = AkShareAnnouncementProvider()
        items = await provider.get_announcements(symbol="600519.SH", limit=10)
        assert len(items) > 0, "Should return at least 1 announcement for 600519.SH"

        first = items[0]
        assert first.symbol == "600519.SH"
        assert first.title != ""
        assert first.source == "东方财富"
        assert first.url.startswith("https://")
        assert first.citation_id.startswith("announcement_600519_SH_")
        assert first.data_quality in ("GOOD", "PARTIAL")
        assert first.retrieved_at != ""
        assert first.content_hash != ""

    @pytest.mark.asyncio
    async def test_announcement_types_present(self):
        """Verify that announcement types are classified."""
        from app.announcements.provider import AkShareAnnouncementProvider
        provider = AkShareAnnouncementProvider()
        items = await provider.get_announcements(symbol="600519.SH", limit=20)
        types = {item.announcement_type for item in items}
        assert len(types) > 1, "Should have multiple announcement types"
        # At least some should not be OTHER
        assert any(t != "OTHER" for t in types), "At least one type should be classified"

    @pytest.mark.asyncio
    async def test_date_filter(self):
        """Test date filtering."""
        from app.announcements.provider import AkShareAnnouncementProvider
        provider = AkShareAnnouncementProvider()
        items = await provider.get_announcements(
            symbol="600519.SH",
            start_date="2026-01-01",
            end_date="2026-08-28",
            limit=20,
        )
        assert len(items) > 0, "Should return announcements for 2026"
        for item in items:
            if item.published_at:
                assert item.published_at >= "2026-01-01"

    @pytest.mark.asyncio
    async def test_published_at_from_source(self):
        """Verify published_at comes from the source, not retrieved_at."""
        from app.announcements.provider import AkShareAnnouncementProvider
        provider = AkShareAnnouncementProvider()
        items = await provider.get_announcements(symbol="600519.SH", limit=5)
        for item in items:
            assert item.published_at != item.retrieved_at, \
                "published_at must come from source, not be equal to retrieved_at"

    @pytest.mark.asyncio
    async def test_dedup(self):
        """Verify no duplicate content_hash in results."""
        from app.announcements.provider import AkShareAnnouncementProvider
        provider = AkShareAnnouncementProvider()
        items = await provider.get_announcements(symbol="600519.SH", limit=20)
        hashes = [item.content_hash for item in items]
        assert len(hashes) == len(set(hashes)), "No duplicate content_hash"


@pytest.mark.integration
class TestRealAnnouncementManager:
    """Test AnnouncementProviderManager with real provider."""

    @pytest.mark.asyncio
    async def test_manager_returns_items(self):
        from app.announcements.provider import AkShareAnnouncementProvider, AnnouncementProviderManager
        manager = AnnouncementProviderManager(providers=[AkShareAnnouncementProvider()])
        items, provider, reason = await manager.get_announcements(symbol="600519.SH", limit=5)
        assert len(items) > 0
        assert provider == "akshare"
        assert reason is None or "empty" not in (reason or "")


@pytest.mark.integration
class TestRealAnnouncementToolE2E:
    """Test the AnnouncementTool handler end-to-end with real AkShare."""

    @pytest.mark.asyncio
    async def test_tool_handler_real(self):
        """Call the tool handler directly with real mode."""
        from app.tools.builtin import ANNOUNCEMENT_TOOL
        from unittest.mock import patch
        with patch("app.market.factory._get_market_data_mode", return_value="real"):
            result = await ANNOUNCEMENT_TOOL.handler(symbol="600519.SH")
        assert result["status"] == "OK"
        assert result["symbol"] == "600519.SH"
        assert result["total"] > 0
        assert result["provider"] == "akshare"

        # Verify item structure
        item = result["items"][0]
        assert "title" in item
        assert "announcement_type" in item
        assert "published_at" in item
        assert "source" in item
        assert "url" in item
        assert "citation_id" in item
        assert "data_quality" in item
        assert item["source"] == "东方财富"

    @pytest.mark.asyncio
    async def test_tool_000001_sz(self):
        """Test with 000001.SZ (平安银行)."""
        from app.tools.builtin import ANNOUNCEMENT_TOOL
        from unittest.mock import patch
        with patch("app.market.factory._get_market_data_mode", return_value="real"):
            result = await ANNOUNCEMENT_TOOL.handler(symbol="000001.SZ")
        assert result["status"] == "OK"
        assert result["total"] > 0
