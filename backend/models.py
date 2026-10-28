"""Legacy model re-exports pointing to modern backend.app.db.models."""
from backend.app.db.models import (
    CheckResult,
    EndpointStatus,
    Incident,
    IncidentEvent,
    IncidentSeverity,
    IncidentStatus,
    MonitoredEndpoint,
)

__all__ = [
    "MonitoredEndpoint",
    "EndpointStatus",
    "CheckResult",
    "Incident",
    "IncidentEvent",
    "IncidentStatus",
    "IncidentSeverity",
]
