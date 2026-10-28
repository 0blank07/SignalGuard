from datetime import datetime

from pydantic import BaseModel


class CheckResultResponse(BaseModel):
    id: int
    endpoint_id: int
    status_code: int | None
    response_time_ms: float
    is_success: bool
    error_type: str | None
    error_message: str | None
    response_snippet: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TriggerCheckResponse(BaseModel):
    endpoint_id: int
    is_success: bool
    status_code: int | None
    response_time_ms: float
    error_type: str | None
    error_message: str | None
    attempts: int
