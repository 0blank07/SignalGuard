
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.db.models.check_result import CheckResult
from backend.app.db.models.endpoint import EndpointStatus, MonitoredEndpoint
from backend.app.db.models.incident import Incident, IncidentEvent, IncidentSeverity, IncidentStatus


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_create_monitored_endpoint(db_session):
    endpoint = MonitoredEndpoint(
        name="Payment Gateway API",
        url="https://api.example.com/health",
        method="GET",
        headers={"Authorization": "Bearer test-key"},
        interval_seconds=30,
        timeout_seconds=5,
        expected_status=200,
        is_active=True,
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(endpoint)

    assert endpoint.id is not None
    assert endpoint.status == EndpointStatus.HEALTHY
    assert endpoint.consecutive_failures == 0
    assert endpoint.consecutive_successes == 0
    assert endpoint.headers == {"Authorization": "Bearer test-key"}
    assert endpoint.created_at is not None


def test_create_check_result(db_session):
    endpoint = MonitoredEndpoint(
        name="Auth Service",
        url="https://auth.example.com/health",
    )
    db_session.add(endpoint)
    db_session.commit()

    check = CheckResult(
        endpoint_id=endpoint.id,
        status_code=200,
        response_time_ms=45.2,
        is_success=True,
        error_type=None,
        error_message=None,
        response_snippet='{"status":"ok"}',
    )
    db_session.add(check)
    db_session.commit()
    db_session.refresh(check)

    assert check.id is not None
    assert check.endpoint_id == endpoint.id
    assert check.is_success is True
    assert check.response_time_ms == 45.2
    assert check.created_at is not None


def test_create_incident_with_events(db_session):
    endpoint = MonitoredEndpoint(
        name="Database Proxy",
        url="https://db.example.com/ping",
    )
    db_session.add(endpoint)
    db_session.commit()

    incident = Incident(
        endpoint_id=endpoint.id,
        status=IncidentStatus.OPEN,
        severity=IncidentSeverity.CRITICAL,
        error_type="TIMEOUT",
        root_cause="Connection timed out after 5.0s",
        failure_count=3,
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    event = IncidentEvent(
        incident_id=incident.id,
        event_type="TRIGGERED",
        message="Endpoint reached 3 consecutive timeouts",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(incident)

    assert incident.id is not None
    assert len(incident.events) == 1
    assert incident.events[0].event_type == "TRIGGERED"
    assert incident.resolved_at is None

    # Resolve incident
    incident.resolve("Service recovered with 2 consecutive 200 OKs")
    db_session.commit()
    db_session.refresh(incident)

    assert incident.status == IncidentStatus.RESOLVED
    assert incident.resolved_at is not None
    assert len(incident.events) == 2
    assert incident.events[1].event_type == "RESOLVED"
