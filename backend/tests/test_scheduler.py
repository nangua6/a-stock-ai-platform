"""Tests for Scheduler service."""
from __future__ import annotations

import asyncio
import pytest

from app.services.scheduler import Scheduler, SchedulerJob


class TestSchedulerJob:
    def test_job_defaults(self):
        async def dummy():
            pass

        job = SchedulerJob(name="test", func=dummy, interval_seconds=60)
        assert job.name == "test"
        assert job.interval_seconds == 60
        assert job.enabled is True
        assert job.last_run is None
        assert job.last_status == "never_run"
        assert job.run_count == 0

    def test_job_to_dict(self):
        async def dummy():
            pass

        job = SchedulerJob(name="test", func=dummy, interval_seconds=60)
        d = job.to_dict()
        assert d["name"] == "test"
        assert d["interval_seconds"] == 60
        assert d["enabled"] is True


class TestScheduler:
    def test_add_job(self):
        scheduler = Scheduler()

        async def dummy():
            pass

        job = scheduler.add_job("test", dummy, 60)
        assert job.name == "test"
        assert "test" in [j.name for j in scheduler._jobs.values()]

    def test_remove_job(self):
        scheduler = Scheduler()

        async def dummy():
            pass

        scheduler.add_job("test", dummy, 60)
        assert scheduler.remove_job("test") is True
        assert "test" not in scheduler._jobs

    def test_remove_nonexistent_job(self):
        scheduler = Scheduler()
        assert scheduler.remove_job("nonexistent") is False

    def test_get_status(self):
        scheduler = Scheduler()

        async def dummy():
            pass

        scheduler.add_job("test", dummy, 60)
        status = scheduler.get_status()
        assert status["running"] is False
        assert status["job_count"] == 1
        assert len(status["jobs"]) == 1

    def test_get_job(self):
        scheduler = Scheduler()

        async def dummy():
            pass

        scheduler.add_job("test", dummy, 60)
        job = scheduler.get_job("test")
        assert job is not None
        assert scheduler.get_job("nonexistent") is None

    @pytest.mark.asyncio
    async def test_start_stop(self):
        scheduler = Scheduler()
        call_count = 0

        async def counting_job():
            nonlocal call_count
            call_count += 1

        # Very short interval for testing
        scheduler.add_job("fast", counting_job, interval_seconds=1)
        await scheduler.start()
        await asyncio.sleep(2.5)  # Wait for a couple of runs
        await scheduler.stop()

        assert call_count >= 2
        job = scheduler.get_job("fast")
        assert job is not None
        assert job.last_status == "success"

    @pytest.mark.asyncio
    async def test_job_error_handling(self):
        scheduler = Scheduler()

        async def failing_job():
            raise ValueError("test error")

        scheduler.add_job("fail", failing_job, interval_seconds=1)
        await scheduler.start()
        await asyncio.sleep(1.5)
        await scheduler.stop()

        job = scheduler.get_job("fail")
        assert job is not None
        assert job.error_count >= 1
        assert job.last_status == "error"

    @pytest.mark.asyncio
    async def test_disabled_job_not_run(self):
        scheduler = Scheduler()
        call_count = 0

        async def counting_job():
            nonlocal call_count
            call_count += 1

        scheduler.add_job("disabled", counting_job, interval_seconds=1, enabled=False)
        await scheduler.start()
        await asyncio.sleep(1.5)
        await scheduler.stop()

        assert call_count == 0
