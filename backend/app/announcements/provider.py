"""Announcement provider interface and AkShare implementation."""
from __future__ import annotations

import hashlib
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.market.base import AnnouncementItem

logger = get_logger("announcements.provider")

# ── AkShare announcement type → our standardized type ─────────────────────────

_TYPE_MAP: Dict[str, str] = {
    "年度报告全文": "ANNUAL_REPORT",
    "年度报告摘要": "ANNUAL_REPORT",
    "年度报告全文(英文)": "ANNUAL_REPORT",
    "年度报告更正公告": "ANNUAL_REPORT",
    "半年度报告全文": "QUARTERLY_REPORT",
    "半年度报告摘要": "QUARTERLY_REPORT",
    "一季度报告全文": "QUARTERLY_REPORT",
    "一季度报告正文": "QUARTERLY_REPORT",
    "三季度报告全文": "QUARTERLY_REPORT",
    "三季度报告正文": "QUARTERLY_REPORT",
    "业绩预告": "EARNINGS_FORECAST",
    "分配预案": "EARNINGS_PREANNOUNCEMENT",
    "分配方案实施": "EARNINGS_PREANNOUNCEMENT",
    "分配方案决议公告": "EARNINGS_PREANNOUNCEMENT",
    "分配方案调整": "EARNINGS_PREANNOUNCEMENT",
    "回购进展情况": "BUYBACK",
    "回购方案修订": "BUYBACK",
    "回购报告书": "BUYBACK",
    "回购预案": "BUYBACK",
    "股东/实际控制人股份增持": "SHAREHOLDER_CHANGE",
    "高管人员持股变动": "SHAREHOLDER_CHANGE",
    "股本变动": "SHAREHOLDER_CHANGE",
    "权益变动报告书": "SHAREHOLDER_CHANGE",
    "股权转让": "SHAREHOLDER_CHANGE",
    "签订协议": "MAJOR_CONTRACT",
    "对外项目投资": "MAJOR_CONTRACT",
    "重大合同": "MAJOR_CONTRACT",
    "上交所股票监管工作函": "REGULATORY",
    "上交所股票监管关注": "REGULATORY",
    "澄清公告": "REGULATORY",
    "风险提示": "RISK_WARNING",
}


def classify_announcement_type(raw_type: str) -> str:
    """Map AkShare announcement type to standardized type. Returns OTHER if unknown."""
    if not raw_type or raw_type in ("", "nan", "None"):
        return "OTHER"
    return _TYPE_MAP.get(raw_type.strip(), "OTHER")


def normalize_symbol(raw: str) -> str:
    """Normalize any stock code format to 600519.SH form. Reuses news provider logic."""
    raw = raw.strip()
    if re.match(r'^\d{6}\.(SH|SZ|BJ)$', raw):
        return raw
    m = re.match(r'^(SH|SZ|BJ)(\d{6})$', raw)
    if m:
        return f"{m.group(2)}.{m.group(1)}"
    m = re.match(r'^(\d{6})$', raw)
    if m:
        code = m.group(1)
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        elif code.startswith(('4', '8')):
            return f"{code}.BJ"
    return raw


def _content_hash(title: str, url: str) -> str:
    """Generate stable dedup hash from title + url."""
    raw = f"{title.strip()}|{url.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_citation_id(symbol: str, published_at: Optional[str], index: int) -> str:
    """Build a traceable citation_id."""
    date_part = "unknown"
    if published_at:
        date_part = published_at[:10].replace("-", "")
    sym = symbol.replace(".", "_") if symbol else "general"
    return f"announcement_{sym}_{date_part}_{index:03d}"


# ── Provider interface ────────────────────────────────────────────────────────

class AnnouncementProvider(ABC):
    """Abstract announcement provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def get_announcements(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        announcement_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[AnnouncementItem]:
        ...


# ── AkShare announcement provider ────────────────────────────────────────────

class AkShareAnnouncementProvider(AnnouncementProvider):
    """Fetches announcements from AkShare (stock_individual_notice_report - EastMoney)."""

    @property
    def name(self) -> str:
        return "akshare"

    async def get_announcements(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        announcement_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[AnnouncementItem]:
        import akshare as ak
        import asyncio

        if not symbol:
            return []

        normalized = normalize_symbol(symbol)
        ak_symbol = normalized.split(".")[0]
        now = datetime.now(timezone.utc).isoformat()

        # Convert dates to AkShare format (YYYYMMDD)
        ak_begin = start_date.replace("-", "") if start_date else None
        ak_end = end_date.replace("-", "") if end_date else None

        try:
            async def _fetch():
                return await asyncio.to_thread(
                    ak.stock_individual_notice_report,
                    security=ak_symbol,
                    symbol="全部",
                    begin_date=ak_begin,
                    end_date=ak_end,
                )

            from app.market.akshare_provider import _retry_call
            df = await _retry_call(
                _fetch,
                operation="get_announcements",
                symbol=normalized,
            )

            if df is None or df.empty:
                return []

            items: List[AnnouncementItem] = []
            seen_hashes: set = set()

            for idx, (_, row) in enumerate(df.head(limit * 2).iterrows()):
                title = str(row.get("公告标题", "")).strip()
                raw_type = str(row.get("公告类型", "")).strip()
                date_raw = str(row.get("公告日期", "")).strip()
                url = str(row.get("网址", "")).strip()
                stock_name = str(row.get("名称", "")).strip()

                if not title:
                    continue

                # Normalize published_at
                published_at = None
                if date_raw and date_raw not in ("", "nan", "None"):
                    published_at = date_raw

                # Classify announcement type
                ann_type = classify_announcement_type(raw_type)

                # Filter by announcement_type if specified
                if announcement_type and ann_type != announcement_type:
                    continue

                # Dedup by content_hash
                chash = _content_hash(title, url)
                if chash in seen_hashes:
                    continue
                seen_hashes.add(chash)

                # Data quality
                quality = "GOOD"
                if not published_at:
                    quality = "PARTIAL"
                if not url:
                    quality = "PARTIAL"

                item = AnnouncementItem(
                    id=f"ann_{ak_symbol}_{idx:04d}",
                    symbol=normalized,
                    name=stock_name,
                    title=title,
                    summary="",
                    content="",
                    announcement_type=ann_type,
                    published_at=published_at,
                    retrieved_at=now,
                    source="东方财富",
                    url=url,
                    citation_id=_build_citation_id(normalized, published_at, idx),
                    data_quality=quality,
                    content_hash=chash,
                )
                items.append(item)

                if len(items) >= limit:
                    break

            # Sort by published_at DESC, None last
            items.sort(key=lambda x: x.published_at or "0000", reverse=True)
            return items

        except Exception as e:
            logger.error("akshare_announcement_failed", symbol=normalized, error=str(e)[:200])
            return []


# ── Announcement manager with fallback ───────────────────────────────────────

class AnnouncementProviderManager:
    """Manages multiple announcement providers with fallback."""

    def __init__(self, providers: Optional[List[AnnouncementProvider]] = None):
        self._providers = providers or []
        self._cache: Dict[str, Tuple[List[AnnouncementItem], float]] = {}
        self._cache_ttl = 300  # 5 minutes

    def register(self, provider: AnnouncementProvider):
        self._providers.append(provider)

    async def get_announcements(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        announcement_type: Optional[str] = None,
        limit: int = 20,
    ) -> Tuple[List[AnnouncementItem], str, Optional[str]]:
        """Get announcements with fallback. Returns (items, provider_used, fallback_reason)."""
        if not self._providers:
            return [], "none", "no_providers_registered"

        # Check cache
        cache_key = f"{symbol}|{start_date or ''}|{end_date or ''}|{announcement_type or ''}|{limit}"
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached[1]) < self._cache_ttl:
            return cached[0], "cache", None

        fallback_reason = None
        for provider in self._providers:
            try:
                items = await provider.get_announcements(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    announcement_type=announcement_type,
                    limit=limit,
                )
                if items:
                    self._cache[cache_key] = (items, time.time())
                    return items, provider.name, fallback_reason
                else:
                    fallback_reason = f"{provider.name}_returned_empty"
            except Exception as e:
                fallback_reason = f"{provider.name}_error:{str(e)[:100]}"
                logger.warning("announcement_provider_failed", provider=provider.name, error=str(e)[:100])

        return [], "none", fallback_reason
