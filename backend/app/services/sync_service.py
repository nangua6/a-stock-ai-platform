"""Data synchronization service.

Orchestrates: Provider -> MarketDataService -> Repository -> DB.
Creates DataSyncJob records for observability. Idempotent, graceful failure.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.market.base import MarketDataProvider
from app.repositories.factory import RepositoryFactory
from app.services.data_quality import DataQualityService
from app.services.market_data_service import MarketDataService
from app.services.technical_analysis import TechnicalAnalysisService

logger = get_logger("sync_service")

_MIN_KLINES_FOR_TA = 30


class SyncService:
    """Orchestrates data synchronization from providers to database."""

    def __init__(self, session: AsyncSession, provider: MarketDataProvider):
        self.session = session
        self.repos = RepositoryFactory(session)
        self.provider = provider
        self.market_data = MarketDataService(session, provider)
        self.quality = DataQualityService()
        self.ta = TechnicalAnalysisService()

    # ── Job management ────────────────────────────────────────────────────

    def _new_job_id(self, job_type: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:6]
        return f"{job_type}_{ts}_{short_id}"

    async def _create_job(self, job_id: str, job_type: str, symbol: Optional[str] = None):
        return await self.repos.sync_jobs.create({
            "job_id": job_id,
            "job_type": job_type,
            "symbol": symbol,
            "status": "RUNNING",
        })

    async def _finish_job(
        self, job_id: str, status: str,
        success_count: int = 0, failed_count: int = 0,
        skipped_count: int = 0, error_message: Optional[str] = None,
        details: Optional[str] = None,
    ):
        await self.repos.sync_jobs.update_status(
            job_id=job_id, status=status,
            success_count=success_count, failed_count=failed_count,
            skipped_count=skipped_count, error_message=error_message,
            details=details,
        )
        await self.session.commit()

    # ── Sync operations ──────────────────────────────────────────────────

    async def sync_stock_list(self) -> Dict[str, Any]:
        """Sync stock list from provider. Idempotent."""
        job_id = self._new_job_id("stock_list")
        await self._create_job(job_id, "stock_list")

        try:
            count = await self.market_data.sync_stock_list()
            await self._finish_job(job_id, "SUCCESS", success_count=count)
            logger.info("stock_list_sync_complete", job_id=job_id, count=count)
            return {"job_id": job_id, "status": "SUCCESS", "count": count}
        except Exception as e:
            await self._finish_job(job_id, "FAILED", error_message=str(e)[:500])
            logger.error("stock_list_sync_failed", job_id=job_id, error=str(e)[:200])
            return {"job_id": job_id, "status": "FAILED", "error": str(e)[:200]}

    async def sync_klines(
        self,
        symbols: List[str],
        timeframe: str = "D",
        limit: int = 200,
    ) -> Dict[str, Any]:
        """Sync klines for multiple symbols. Single failure does not stop batch."""
        job_id = self._new_job_id("kline")
        await self._create_job(job_id, "kline")

        success = 0
        failed = 0
        skipped = 0
        errors: List[Dict] = []
        quality_issues = 0

        for symbol in symbols:
            try:
                klines = await self.provider.get_kline(symbol, timeframe=timeframe, limit=limit)
                if not klines:
                    skipped += 1
                    continue

                validation = self.quality.validate_klines(klines)
                valid_klines = validation["valid_klines"]
                if validation["invalid"] > 0:
                    quality_issues += validation["invalid"]
                    logger.warning(
                        "kline_quality_issues",
                        symbol=symbol,
                        invalid=validation["invalid"],
                    )

                if not valid_klines:
                    failed += 1
                    errors.append({"symbol": symbol, "error": "all_klines_invalid"})
                    continue

                data = [
                    {
                        "symbol": k.symbol,
                        "trade_date": k.trade_date,
                        "timeframe": k.timeframe,
                        "open": k.open,
                        "high": k.high,
                        "low": k.low,
                        "close": k.close,
                        "volume": k.volume,
                        "amount": k.amount,
                        "change_pct": k.change_pct,
                        "data_source": k.data_source,
                        "available_time": k.available_time,
                    }
                    for k in valid_klines
                ]
                await self.repos.klines.bulk_upsert(data)
                await self.session.commit()
                success += 1

            except Exception as e:
                failed += 1
                errors.append({"symbol": symbol, "error": str(e)[:200]})
                logger.warning("kline_sync_failed", symbol=symbol, error=str(e)[:200])
                continue

        status = "SUCCESS" if failed == 0 else ("PARTIAL_SUCCESS" if success > 0 else "FAILED")
        details = json.dumps({"errors": errors[:20], "quality_issues": quality_issues}) if errors else None

        await self._finish_job(
            job_id, status,
            success_count=success, failed_count=failed,
            skipped_count=skipped,
            error_message=f"{failed} symbols failed" if failed > 0 else None,
            details=details,
        )

        logger.info("kline_sync_complete", job_id=job_id, success=success, failed=failed)
        return {"job_id": job_id, "status": status, "success": success, "failed": failed}

    async def compute_technical_snapshots(
        self,
        symbols: List[str],
        lookback: int = 120,
    ) -> Dict[str, Any]:
        """Compute and persist technical indicators for given symbols."""
        job_id = self._new_job_id("technical")
        await self._create_job(job_id, "technical")

        success = 0
        failed = 0
        errors: List[Dict] = []

        from app.market.base import KlineData as KlineDataDC

        for symbol in symbols:
            try:
                # Get full kline models from DB
                kline_models = await self.repos.klines.get_by_symbol(symbol, limit=lookback)
                if not kline_models or len(kline_models) < _MIN_KLINES_FOR_TA:
                    logger.info("insufficient_klines", symbol=symbol, count=len(kline_models) if kline_models else 0)
                    failed += 1
                    errors.append({"symbol": symbol, "error": "insufficient_klines"})
                    continue

                # Convert ORM models to dataclass KlineData for TA
                kline_data = [
                    KlineDataDC(
                        symbol=k.symbol, trade_date=k.trade_date, timeframe=k.timeframe,
                        open=k.open, high=k.high, low=k.low, close=k.close,
                        volume=k.volume, amount=k.amount,
                        change_pct=k.change_pct or 0.0, turnover=k.turnover or 0.0,
                        data_source=k.data_source, available_time=k.available_time or "",
                    )
                    for k in kline_models
                ]

                indicators = self.ta.compute(kline_data)
                trade_date = kline_models[-1].trade_date

                await self.repos.technical_snapshots.upsert({
                    "symbol": symbol,
                    "trade_date": trade_date,
                    "ma5": indicators.ma5,
                    "ma10": indicators.ma10,
                    "ma20": indicators.ma20,
                    "ma60": indicators.ma60,
                    "ema12": indicators.ema12,
                    "ema26": indicators.ema26,
                    "macd_line": indicators.macd_line,
                    "macd_signal": indicators.macd_signal,
                    "macd_histogram": indicators.macd_histogram,
                    "rsi": indicators.rsi,
                    "kdj_k": indicators.kdj_k,
                    "kdj_d": indicators.kdj_d,
                    "kdj_j": indicators.kdj_j,
                    "boll_upper": indicators.boll_upper,
                    "boll_middle": indicators.boll_middle,
                    "boll_lower": indicators.boll_lower,
                    "atr": indicators.atr,
                    "volume_ma5": indicators.volume_ma5,
                    "volume_ma10": indicators.volume_ma10,
                    "volume_ma20": indicators.volume_ma20,
                    "volatility": indicators.volatility,
                    "turnover_rate": indicators.turnover_rate,
                    "amplitude": indicators.amplitude,
                    "period": indicators.period,
                    "data_source": kline_models[-1].data_source,
                })
                await self.session.commit()
                success += 1

            except Exception as e:
                failed += 1
                errors.append({"symbol": symbol, "error": str(e)[:200]})
                logger.warning("technical_snapshot_failed", symbol=symbol, error=str(e)[:200])
                continue

        status = "SUCCESS" if failed == 0 else ("PARTIAL_SUCCESS" if success > 0 else "FAILED")
        details = json.dumps(errors[:20]) if errors else None

        await self._finish_job(
            job_id, status,
            success_count=success, failed_count=failed,
            error_message=f"{failed} symbols failed" if failed > 0 else None,
            details=details,
        )

        logger.info("technical_snapshot_complete", job_id=job_id, success=success, failed=failed)
        return {"job_id": job_id, "status": status, "success": success, "failed": failed}

    async def compute_analysis_snapshots(
        self,
        symbols: List[str],
    ) -> Dict[str, Any]:
        """Combine quote + technical + risk into analysis snapshots. No LLM."""
        from app.agents.stock_analysis_agent import StockAnalysisAgent
        from app.market.provider_manager import ProviderManager

        job_id = self._new_job_id("analysis")
        await self._create_job(job_id, "analysis")

        success = 0
        failed = 0
        errors: List[Dict] = []

        # Create agent with the same provider
        if isinstance(self.provider, ProviderManager):
            agent = StockAnalysisAgent(self.provider)
        else:
            # Wrap single provider in a manager for the agent
            pm = ProviderManager([self.provider])
            agent = StockAnalysisAgent(pm)

        for symbol in symbols:
            try:
                result = await agent.analyze(symbol)
                trade_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                await self.repos.analysis_snapshots.upsert({
                    "symbol": symbol,
                    "name": result.name,
                    "trade_date": trade_date,
                    "current_price": result.technical.score,  # placeholder
                    "change_pct": 0.0,
                    "volume": 0.0,
                    "amount": 0.0,
                    "technical_score": result.technical.score,
                    "fundamental_score": result.fundamental_score,
                    "overall_score": result.overall_score,
                    "recommendation": result.recommendation.value if hasattr(result.recommendation, "value") else str(result.recommendation),
                    "confidence": result.confidence,
                    "technical_detail": result.technical.to_dict(),
                    "risk_level": result.risk.risk_level,
                    "risk_details": result.risk.to_dict(),
                    "bull_case": result.bull_case,
                    "bear_case": result.bear_case,
                    "key_risks": {"risks": result.key_risks},
                    "data_quality": result.data_quality.value if hasattr(result.data_quality, "value") else str(result.data_quality),
                    "data_source": result.data_source,
                })
                await self.session.commit()
                success += 1

            except Exception as e:
                failed += 1
                errors.append({"symbol": symbol, "error": str(e)[:200]})
                logger.warning("analysis_snapshot_failed", symbol=symbol, error=str(e)[:200])
                continue

        status = "SUCCESS" if failed == 0 else ("PARTIAL_SUCCESS" if success > 0 else "FAILED")
        details = json.dumps(errors[:20]) if errors else None

        await self._finish_job(
            job_id, status,
            success_count=success, failed_count=failed,
            error_message=f"{failed} symbols failed" if failed > 0 else None,
            details=details,
        )

        logger.info("analysis_snapshot_complete", job_id=job_id, success=success, failed=failed)
        return {"job_id": job_id, "status": status, "success": success, "failed": failed}

    async def sync_full(self, symbols: List[str]) -> Dict[str, Any]:
        """Full pipeline: stock_list + klines + technical + analysis."""
        results: Dict[str, Any] = {}

        # Step 1: Stock list
        results["stock_list"] = await self.sync_stock_list()

        # Step 2: Klines
        results["klines"] = await self.sync_klines(symbols)

        # Step 3: Technical snapshots
        results["technical"] = await self.compute_technical_snapshots(symbols)

        # Step 4: Analysis snapshots
        results["analysis"] = await self.compute_analysis_snapshots(symbols)

        return results

    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status summary."""
        running = await self.repos.sync_jobs.get_running_jobs()
        recent = await self.repos.sync_jobs.get_recent(limit=10)

        return {
            "running_jobs": len(running),
            "recent_jobs": [
                {
                    "job_id": j.job_id,
                    "job_type": j.job_type,
                    "status": j.status,
                    "success_count": j.success_count,
                    "failed_count": j.failed_count,
                    "created_at": str(j.created_at) if j.created_at else None,
                }
                for j in recent
            ],
        }

    async def get_sync_history(self, job_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get sync job history."""
        jobs = await self.repos.sync_jobs.get_recent(job_type=job_type, limit=limit)
        return [
            {
                "job_id": j.job_id,
                "job_type": j.job_type,
                "status": j.status,
                "success_count": j.success_count,
                "failed_count": j.failed_count,
                "skipped_count": j.skipped_count,
                "error_message": j.error_message,
                "created_at": str(j.created_at) if j.created_at else None,
            }
            for j in jobs
        ]
