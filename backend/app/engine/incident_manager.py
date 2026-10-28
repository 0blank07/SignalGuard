from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db.base import utc_now
from backend.app.db.models.check_result import CheckResult
from backend.app.db.models.endpoint import EndpointStatus, MonitoredEndpoint
from backend.app.db.models.incident import Incident, IncidentEvent, IncidentSeverity, IncidentStatus
from backend.app.engine.prober import ProbeExecutionSummary
from backend.app.engine.state_machine import evaluate_health_transition


@dataclass
class IncidentUpdateResult:
    endpoint_id: int
    previous_status: EndpointStatus
    current_status: EndpointStatus
    incident_created: bool
    incident_resolved: bool
    active_incident_id: int | None


class IncidentManager:
    def __init__(
        self,
        failure_threshold: int | None = None,
        recovery_threshold: int | None = None,
    ) -> None:
        settings = get_settings()
        self.failure_threshold = (
            failure_threshold or settings.CONSECUTIVE_FAILURES_FOR_INCIDENT
        )
        self.recovery_threshold = (
            recovery_threshold or settings.CONSECUTIVE_SUCCESSES_FOR_RECOVERY
        )

    def record_probe_result(
        self,
        db: Session,
        endpoint_id: int,
        summary: ProbeExecutionSummary,
    ) -> IncidentUpdateResult:
        """Processes probe execution, records check result, and manages incident lifecycle idempotently."""
        now = utc_now()

        # 1. Fetch endpoint
        endpoint = db.query(MonitoredEndpoint).filter(MonitoredEndpoint.id == endpoint_id).first()
        if not endpoint:
            raise ValueError(f"Endpoint with id {endpoint_id} not found")

        previous_status = endpoint.status

        # 2. Persist CheckResult
        check_result = CheckResult(
            endpoint_id=endpoint.id,
            status_code=summary.status_code,
            response_time_ms=summary.response_time_ms,
            is_success=summary.is_success,
            error_type=summary.error_type,
            error_message=summary.error_message,
            response_snippet=summary.response_snippet,
            created_at=now,
        )
        db.add(check_result)

        # 3. Update consecutive counters
        if summary.is_success:
            endpoint.consecutive_successes += 1
            endpoint.consecutive_failures = 0
        else:
            endpoint.consecutive_failures += 1
            endpoint.consecutive_successes = 0

        endpoint.last_checked_at = now
        endpoint.next_check_due = now + timedelta(seconds=endpoint.interval_seconds)

        # 4. State Machine Transition
        new_status, status_changed = evaluate_health_transition(
            current_status=endpoint.status,
            probe_success=summary.is_success,
            consecutive_failures=endpoint.consecutive_failures,
            consecutive_successes=endpoint.consecutive_successes,
            failure_threshold=self.failure_threshold,
            recovery_threshold=self.recovery_threshold,
        )
        endpoint.status = new_status

        # 5. Query for any currently ACTIVE (OPEN or ACKNOWLEDGED) incident
        active_incident = (
            db.query(Incident)
            .filter(
                Incident.endpoint_id == endpoint.id,
                Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED]),
            )
            .first()
        )

        incident_created = False
        incident_resolved = False

        if new_status == EndpointStatus.DOWN:
            if active_incident:
                # Deduplication: update existing open incident
                active_incident.last_seen_at = now
                active_incident.failure_count += 1
                if summary.error_type and not active_incident.error_type:
                    active_incident.error_type = summary.error_type
            else:
                # Open single new incident
                active_incident = Incident(
                    endpoint_id=endpoint.id,
                    status=IncidentStatus.OPEN,
                    severity=IncidentSeverity.HIGH,
                    error_type=summary.error_type or "PROBE_FAILURE",
                    root_cause=summary.error_message or "Probe execution failed threshold",
                    started_at=now,
                    last_seen_at=now,
                    failure_count=endpoint.consecutive_failures,
                    created_at=now,
                )
                db.add(active_incident)
                db.flush()  # populate active_incident.id

                event = IncidentEvent(
                    incident_id=active_incident.id,
                    event_type="TRIGGERED",
                    message=f"Endpoint transitioned to DOWN: {summary.error_message or 'Health check failures'}",
                    created_at=now,
                )
                db.add(event)
                incident_created = True

        elif new_status == EndpointStatus.HEALTHY and active_incident:
            # Recovery: resolve the active incident
            active_incident.resolve(
                f"Endpoint recovered to HEALTHY after {endpoint.consecutive_successes} consecutive successful checks."
            )
            incident_resolved = True

        return IncidentUpdateResult(
            endpoint_id=endpoint.id,
            previous_status=previous_status,
            current_status=new_status,
            incident_created=incident_created,
            incident_resolved=incident_resolved,
            active_incident_id=active_incident.id if active_incident else None,
        )
