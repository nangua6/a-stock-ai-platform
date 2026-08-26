"""Common response schemas."""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API envelope."""
    success: bool = True
    code: int = 200
    message: str = "ok"
    data: Optional[T] = None


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
