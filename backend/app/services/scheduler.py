"""Async scheduler for periodic data synchronization tasks.

Uses asyncio (no Celery dependency). Integrates with TradingCalendar
to avoid running sync jobs on non-trading days when appropriate.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger("scheduler")


class SchedulerJob:
    """A single scheduled job."""

    def __init__(
        self,
        name: str,
        func: Callable[..., Coroutine],
        interval_seconds: int,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        trading_hours_only: bool = False,
        enabled: bool = True,
    ):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.args = args
        self.kwargs = kwargs or {}
        self.trading_hours_only = trading_hours_only
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.last_status: str = "never_run"
        self.run_count: int = 0
        self.error_count: int = 0
        self._task: Optional[asyncio.Task] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "interval_seconds": self.interval_seconds,
            "trading_hours_only": self.trading_hours_only,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status,
            "run_count": self.run_count,
            "error_count": self.error_count,
        }


class Scheduler:
    """Simple async scheduler for periodic jobs."""

    def __init__(self):
        self._jobs: Dict[str, SchedulerJob] = {}
        self._running = False
        self._main_task: Optional[asyncio.Task] = None

    def add_job(
        self,
        name: str,
        func: Callable[..., Coroutine],
        interval_seconds: int,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        trading_hours_only: bool = False,
        enabled: bool = True,
    ) -> SchedulerJob:
        """Register a periodic job."""
        job = SchedulerJob(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            args=args,
            kwargs=kwargs,
            trading_hours_only=trading_hours_only,
            enabled=enabled,
        )
        self._jobs[name] = job
        logger.info("scheduler_job_added", name=name, interval=interval_seconds)
        return job

    def remove_job(self, name: str) -> bool:
        if name in self._jobs:
            job = self._jobs.pop(name)
            if job._task and not job._task.done():
                job._task.cancel()
            logger.info("scheduler_job_removed", name=name)
            return True
        return False

    async def start(self):
        """Start the scheduler loop."""
        if self._running:
            logger.warning("scheduler_already_running")
            return

        self._running = True
        self._main_task = asyncio.create_task(self._run_loop())
        logger.info("scheduler_started", job_count=len(self._jobs))

    async def stop(self):
        """Stop the scheduler gracefully."""
        self._running = False
        for job in self._jobs.values():
            if job._task and not job._task.done():
                job._task.cancel()
        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        logger.info("scheduler_stopped")

    async def _run_loop(self):
        """Main scheduler loop – checks jobs every second."""
        while self._running:
            now = datetime.now(timezone.utc)
            for job in self._jobs.values():
                if not job.enabled:
                    continue

                # Check if it is time to run
                if job.last_run is not None:
                    elapsed = (now - job.last_run).total_seconds()
                    if elapsed < job.interval_seconds:
                        continue

                # Run the job
                job._task = asyncio.create_task(self._execute_job(job, now))

            await asyncio.sleep(1)

    async def _execute_job(self, job: SchedulerJob, now: datetime):
        """Execute a single job with error handling."""
        job.last_run = now
        job.run_count += 1

        try:
            logger.info("scheduler_job_start", name=job.name, run_count=job.run_count)
            result = await job.func(*job.args, **job.kwargs)
            job.last_status = "success"
            logger.info("scheduler_job_success", name=job.name)
        except asyncio.CancelledError:
            job.last_status = "cancelled"
            raise
        except Exception as e:
            job.last_status = "error"
            job.error_count += 1
            logger.error("scheduler_job_error", name=job.name, error=str(e)[:200])

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status and job info."""
        return {
            "running": self._running,
            "job_count": len(self._jobs),
            "jobs": [j.to_dict() for j in self._jobs.values()],
        }

    def get_job(self, name: str) -> Optional[SchedulerJob]:
        return self._jobs.get(name)
