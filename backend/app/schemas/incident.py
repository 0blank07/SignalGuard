from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.db.models.incident import IncidentSeverity, IncidentStatus


class IncidentEventResponse(BaseModel):
    id: int
    event_type: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentResponse(BaseModel):
    id: int
    endpoint_id: int
    status: IncidentStatus
    severity: IncidentSeverity
    error_type: str
    root_cause: str
    started_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None
    failure_count: int
    created_at: datetime
    updated_at: datetime
    events: list[IncidentEventResponse] = []

    class Config:
        from_attributes = True


class ResolveIncidentRequest(BaseModel):
    message: str = Field(default="Incident resolved manually by operator", min_length=1)
