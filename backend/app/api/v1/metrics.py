from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.api.deps import verify_api_key
from backend.app.config import get_settings
from backend.app.core.errors import NotFoundError
from backend.app.db.base import utc_now
from backend.app.db.models.endpoint import EndpointStatus, MonitoredEndpoint
from backend.app.db.models.incident import Incident, IncidentStatus
from backend.app.db.session import get_db
from backend.app.engine.metrics_calculator import MetricsCalculator
from backend.app.schemas.metrics import EndpointMetricsResponse, SystemHealthResponse


router = APIRouter(tags=["Metrics & Health"])


@router.get("/endpoints/{endpoint_id}/metrics", response_model=EndpointMetricsResponse)
def get_endpoint_metrics(
    endpoint_id: int,
    limit: int = 1000,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise NotFoundError("MonitoredEndpoint", endpoint_id)

    return MetricsCalculator.calculate_endpoint_metrics(db, endpoint, limit=limit)


@router.get("/health", response_model=SystemHealthResponse)
def get_system_health(db: Session = Depends(get_db)):
    settings = get_settings()

    db_status = "connected"
    try:
        db.execute(text("SELECT 1")).scalar()
    except Exception:
        db_status = "error"

    active_count = (
        db.query(MonitoredEndpoint)
        .filter(MonitoredEndpoint.is_active.is_(True), MonitoredEndpoint.status != EndpointStatus.PAUSED)
        .count()
    )
    open_incidents_count = (
        db.query(Incident)
        .filter(Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED]))
        .count()
    )

    return SystemHealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        version=settings.VERSION,
        database=db_status,
        scheduler="running",
        active_monitors=active_count,
        open_incidents=open_incidents_count,
        timestamp=utc_now(),
    )
