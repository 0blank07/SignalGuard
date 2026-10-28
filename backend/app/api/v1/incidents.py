import math
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.api.deps import verify_api_key
from backend.app.core.errors import NotFoundError
from backend.app.db.models.incident import Incident, IncidentStatus
from backend.app.db.session import get_db
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.incident import IncidentResponse, ResolveIncidentRequest


router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=PaginatedResponse[IncidentResponse])
def list_incidents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    endpoint_id: int | None = None,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    query = db.query(Incident)
    if status_filter:
        query = query.filter(Incident.status == status_filter)
    if endpoint_id:
        query = query.filter(Incident.endpoint_id == endpoint_id)

    total = query.count()
    items = (
        query.order_by(Incident.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse[IncidentResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise NotFoundError("Incident", incident_id)
    return incident


@router.post("/{incident_id}/acknowledge", response_model=IncidentResponse)
def acknowledge_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise NotFoundError("Incident", incident_id)

    incident.acknowledge("Incident acknowledged by operator via API")
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/resolve", response_model=IncidentResponse)
def resolve_incident(
    incident_id: int,
    payload: ResolveIncidentRequest | None = None,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise NotFoundError("Incident", incident_id)

    msg = payload.message if payload else "Incident resolved manually via API"
    incident.resolve(msg)
    db.commit()
    db.refresh(incident)
    return incident
