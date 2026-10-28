from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.app.db.models.endpoint import EndpointStatus


class EndpointBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., description="Target URL for monitoring")
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")
    headers: dict[str, Any] | None = None
    body: str | None = None
    interval_seconds: int = Field(default=30, ge=5, le=86400)
    timeout_seconds: int = Field(default=10, ge=1, le=60)
    expected_status: int = Field(default=200, ge=100, le=599)
    retry_count: int = Field(default=3, ge=1, le=10)


class EndpointCreate(EndpointBase):
    pass


class EndpointUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = None
    method: str | None = Field(default=None, pattern="^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")
    headers: dict[str, Any] | None = None
    body: str | None = None
    interval_seconds: int | None = Field(default=None, ge=5, le=86400)
    timeout_seconds: int | None = Field(default=None, ge=1, le=60)
    expected_status: int | None = Field(default=None, ge=100, le=599)
    retry_count: int | None = Field(default=None, ge=1, le=10)
    is_active: bool | None = None


class EndpointResponse(EndpointBase):
    id: int
    is_active: bool
    status: EndpointStatus
    last_checked_at: datetime | None
    next_check_due: datetime
    consecutive_failures: int
    consecutive_successes: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
