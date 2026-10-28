import math
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.api.deps import verify_api_key
from backend.app.config import get_settings
from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.core.security import validate_target_url
from backend.app.db.models.endpoint import EndpointStatus, MonitoredEndpoint
from backend.app.db.session import get_db
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.endpoint import EndpointCreate, EndpointResponse, EndpointUpdate


router = APIRouter(prefix="/endpoints", tags=["Endpoints"])


@router.post("", response_model=EndpointResponse, status_code=status.HTTP_201_CREATED)
def create_endpoint(
    payload: EndpointCreate,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    settings = get_settings()
    # SSRF Protection validation
    validate_target_url(payload.url, allow_private=settings.ALLOW_PRIVATE_IPS)

    endpoint = MonitoredEndpoint(
        name=payload.name,
        url=payload.url,
        method=payload.method,
        headers=payload.headers,
        body=payload.body,
        interval_seconds=payload.interval_seconds,
        timeout_seconds=payload.timeout_seconds,
        expected_status=payload.expected_status,
        retry_count=payload.retry_count,
        is_active=True,
        status=EndpointStatus.HEALTHY,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.get("", response_model=PaginatedResponse[EndpointResponse])
def list_endpoints(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: EndpointStatus | None = Query(default=None, alias="status"),
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    query = db.query(MonitoredEndpoint)
    if status_filter:
        query = query.filter(MonitoredEndpoint.status == status_filter)
    if is_active is not None:
        query = query.filter(MonitoredEndpoint.is_active == is_active)

    total = query.count()
    items = (
        query.order_by(MonitoredEndpoint.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse[EndpointResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{endpoint_id}", response_model=EndpointResponse)
def get_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise NotFoundError("MonitoredEndpoint", endpoint_id)
    return endpoint


@router.patch("/{endpoint_id}", response_model=EndpointResponse)
def update_endpoint(
    endpoint_id: int,
    payload: EndpointUpdate,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise NotFoundError("MonitoredEndpoint", endpoint_id)

    settings = get_settings()
    update_data = payload.model_dump(exclude_unset=True)

    if "url" in update_data and update_data["url"] is not None:
        validate_target_url(update_data["url"], allow_private=settings.ALLOW_PRIVATE_IPS)

    for key, value in update_data.items():
        setattr(endpoint, key, value)

    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise NotFoundError("MonitoredEndpoint", endpoint_id)
    db.delete(endpoint)
    db.commit()
    return None


@router.post("/{endpoint_id}/pause", response_model=EndpointResponse)
def pause_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise NotFoundError("MonitoredEndpoint", endpoint_id)
    endpoint.status = EndpointStatus.PAUSED
    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.post("/{endpoint_id}/resume", response_model=EndpointResponse)
def resume_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise NotFoundError("MonitoredEndpoint", endpoint_id)
    if endpoint.status == EndpointStatus.PAUSED:
        endpoint.status = EndpointStatus.HEALTHY
    db.commit()
    db.refresh(endpoint)
    return endpoint
