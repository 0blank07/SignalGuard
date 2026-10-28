import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import verify_api_key
from backend.app.core.errors import NotFoundError
from backend.app.db.models.check_result import CheckResult
from backend.app.db.models.endpoint import MonitoredEndpoint
from backend.app.db.session import get_db
from backend.app.engine.incident_manager import IncidentManager
from backend.app.engine.prober import execute_probe
from backend.app.schemas.check import CheckResultResponse, TriggerCheckResponse
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/endpoints", tags=["Checks"])


@router.post("/{endpoint_id}/check", response_model=TriggerCheckResponse)
async def trigger_immediate_check(
    endpoint_id: int,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise NotFoundError("MonitoredEndpoint", endpoint_id)

    # Detach attributes
    detached_endpoint = MonitoredEndpoint(
        id=endpoint.id,
        name=endpoint.name,
        url=endpoint.url,
        method=endpoint.method,
        headers=endpoint.headers,
        body=endpoint.body,
        timeout_seconds=endpoint.timeout_seconds,
        expected_status=endpoint.expected_status,
        retry_count=endpoint.retry_count,
    )

    summary = await execute_probe(endpoint=detached_endpoint)

    manager = IncidentManager()
    manager.record_probe_result(db, endpoint.id, summary)
    db.commit()

    return TriggerCheckResponse(
        endpoint_id=endpoint.id,
        is_success=summary.is_success,
        status_code=summary.status_code,
        response_time_ms=summary.response_time_ms,
        error_type=summary.error_type,
        error_message=summary.error_message,
        attempts=summary.attempts,
    )


@router.get("/{endpoint_id}/history", response_model=PaginatedResponse[CheckResultResponse])
def get_check_history(
    endpoint_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise NotFoundError("MonitoredEndpoint", endpoint_id)

    query = db.query(CheckResult).filter(CheckResult.endpoint_id == endpoint_id)
    total = query.count()
    items = (
        query.order_by(CheckResult.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse[CheckResultResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
