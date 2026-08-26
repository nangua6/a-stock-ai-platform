"""DataSyncJob repository."""
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_job import DataSyncJob
from app.repositories.base import BaseRepository


class SyncJobRepository(BaseRepository[DataSyncJob]):
    def __init__(self, session: AsyncSession):
        super().__init__(DataSyncJob, session)

    async def get_by_job_id(self, job_id: str) -> Optional[DataSyncJob]:
        return await self.find_one(job_id=job_id)

    async def get_recent(self, job_type: Optional[str] = None, limit: int = 20) -> List[DataSyncJob]:
        filters = {}
        if job_type:
            filters["job_type"] = job_type
        return await self.find_many(limit=limit, order_by="created_at", descending=True, **filters)

    async def get_running_jobs(self) -> List[DataSyncJob]:
        return await self.find_many(status="RUNNING", limit=100)

    async def update_status(
        self, job_id: str, status: str,
        success_count: int = 0, failed_count: int = 0,
        skipped_count: int = 0, error_message: Optional[str] = None,
        details: Optional[str] = None,
    ) -> Optional[DataSyncJob]:
        job = await self.get_by_job_id(job_id)
        if not job:
            return None
        return await self.update(job.id, {
            "status": status,
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "error_message": error_message,
            "details": details,
        })
