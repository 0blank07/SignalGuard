from datetime import datetime

from pydantic import BaseModel


class EndpointMetricsResponse(BaseModel):
    endpoint_id: int
    endpoint_name: str
    total_checks: int
    successful_checks: int
    failed_checks: int
    uptime_percentage: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    last_checked_at: datetime | None


class SystemHealthResponse(BaseModel):
    status: str
    version: str
    database: str
    scheduler: str
    active_monitors: int
    open_incidents: int
    timestamp: datetime
