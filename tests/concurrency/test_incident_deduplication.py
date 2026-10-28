import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.base import Base
from backend.app.db.models.endpoint import MonitoredEndpoint, EndpointStatus
from backend.app.db.models.incident import Incident, IncidentStatus
from backend.app.db.models.check_result import CheckResult
from backend.app.engine.incident_manager import IncidentManager
from backend.app.engine.prober import ProbeExecutionSummary


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


def test_incident_manager_creates_single_incident(db_session):
    manager = IncidentManager()
    endpoint = MonitoredEndpoint(
        name="Checkout Service",
        url="https://checkout.example.com",
    )
    db_session.add(endpoint)
    db_session.commit()

    # 1st failure -> degraded (threshold=2)
    summary_1 = ProbeExecutionSummary(
        endpoint_id=endpoint.id,
        url=endpoint.url,
        is_success=False,
        status_code=500,
        response_time_ms=120.0,
        error_type="HTTP_ERROR",
        error_message="500 Internal Server Error",
        response_snippet=None,
        attempts=3,
    )
    manager.record_probe_result(db_session, endpoint.id, summary_1)
    db_session.commit()

    incidents = db_session.query(Incident).filter(Incident.endpoint_id == endpoint.id).all()
    assert len(incidents) == 0  # not DOWN yet

    # 2nd failure -> reaches threshold -> creates ONE incident
    summary_2 = ProbeExecutionSummary(
        endpoint_id=endpoint.id,
        url=endpoint.url,
        is_success=False,
        status_code=500,
        response_time_ms=115.0,
        error_type="HTTP_ERROR",
        error_message="500 Internal Server Error",
        response_snippet=None,
        attempts=3,
    )
    manager.record_probe_result(db_session, endpoint.id, summary_2)
    db_session.commit()

    incidents = db_session.query(Incident).filter(Incident.endpoint_id == endpoint.id).all()
    assert len(incidents) == 1
    assert incidents[0].status == IncidentStatus.OPEN
    assert incidents[0].failure_count == 2

    # 3rd failure while already down -> MUST NOT create a second incident
    summary_3 = ProbeExecutionSummary(
        endpoint_id=endpoint.id,
        url=endpoint.url,
        is_success=False,
        status_code=500,
        response_time_ms=110.0,
        error_type="HTTP_ERROR",
        error_message="500 Internal Server Error",
        response_snippet=None,
        attempts=3,
    )
    manager.record_probe_result(db_session, endpoint.id, summary_3)
    db_session.commit()

    incidents = db_session.query(Incident).filter(Incident.endpoint_id == endpoint.id).all()
    assert len(incidents) == 1
    assert incidents[0].failure_count == 3


def test_incident_manager_resolves_on_recovery(db_session):
    manager = IncidentManager()
    endpoint = MonitoredEndpoint(
        name="User Service",
        url="https://user.example.com",
    )
    db_session.add(endpoint)
    db_session.commit()

    fail_summary = ProbeExecutionSummary(
        endpoint_id=endpoint.id,
        url=endpoint.url,
        is_success=False,
        status_code=503,
        response_time_ms=100.0,
        error_type="HTTP_ERROR",
        error_message="Service Unavailable",
        response_snippet=None,
        attempts=3,
    )
    # 2 failures -> DOWN -> incident opened
    manager.record_probe_result(db_session, endpoint.id, fail_summary)
    manager.record_probe_result(db_session, endpoint.id, fail_summary)
    db_session.commit()

    active_incidents = (
        db_session.query(Incident)
        .filter(Incident.endpoint_id == endpoint.id, Incident.status == IncidentStatus.OPEN)
        .all()
    )
    assert len(active_incidents) == 1

    success_summary = ProbeExecutionSummary(
        endpoint_id=endpoint.id,
        url=endpoint.url,
        is_success=True,
        status_code=200,
        response_time_ms=30.0,
        error_type=None,
        error_message=None,
        response_snippet="OK",
        attempts=1,
    )

    # 1st recovery success -> DEGRADED
    manager.record_probe_result(db_session, endpoint.id, success_summary)
    db_session.commit()
    assert (
        db_session.query(Incident)
        .filter(Incident.endpoint_id == endpoint.id, Incident.status == IncidentStatus.OPEN)
        .count()
        == 1
    )

    # 2nd recovery success -> HEALTHY -> Incident auto-resolved!
    manager.record_probe_result(db_session, endpoint.id, success_summary)
    db_session.commit()

    resolved_incident = (
        db_session.query(Incident)
        .filter(Incident.endpoint_id == endpoint.id, Incident.status == IncidentStatus.RESOLVED)
        .first()
    )
    assert resolved_incident is not None
    assert resolved_incident.resolved_at is not None
    assert (
        db_session.query(Incident)
        .filter(Incident.endpoint_id == endpoint.id, Incident.status == IncidentStatus.OPEN)
        .count()
        == 0
    )
