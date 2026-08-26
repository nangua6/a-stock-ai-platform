"""Data sync job tracking model."""
from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class DataSyncJob(BaseModel):
    """Tracks data synchronization jobs for observability and recovery."""
    __tablename__ = "data_sync_jobs"

    job_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # stock_list_sync | kline_sync | quote_sync | full_sync
    symbol: Mapped[str | None] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING")
    # RUNNING | SUCCESS | PARTIAL_SUCCESS | FAILED
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[str | None] = mapped_column(Text)  # JSON string with per-item results
    data_timestamp: Mapped[str | None] = mapped_column(String(30))  # When the source data was produced
