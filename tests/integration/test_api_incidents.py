import pytest
import httpx
from backend.app.db.models.endpoint import MonitoredEndpoint
from backend.app.db.models.incident import Incident, IncidentStatus, IncidentSeverity
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_get_incidents_and_lifecycle(async_client: httpx.AsyncClient, test_db: Session):
    # Setup endpoint & incident in test_db
    endpoint = MonitoredEndpoint(name="Billing API", url="https://api.github.com/status")
    test_db.add(endpoint)
    test_db.commit()

    incident = Incident(
        endpoint_id=endpoint.id,
        status=IncidentStatus.OPEN,
        severity=IncidentSeverity.HIGH,
        error_type="TIMEOUT",
        root_cause="Read timeout after 5.0s",
        failure_count=3,
    )
    test_db.add(incident)
    test_db.commit()

    # 1. Query incidents list
    res = await async_client.get("/api/v1/incidents?status=OPEN")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["error_type"] == "TIMEOUT"

    # 2. Acknowledge incident
    ack_res = await async_client.post(f"/api/v1/incidents/{incident.id}/acknowledge")
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"

    # 3. Resolve incident
    resolve_res = await async_client.post(
        f"/api/v1/incidents/{incident.id}/resolve",
        json={"message": "Resolved manually after failover"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"
    assert resolve_res.json()["resolved_at"] is not None
