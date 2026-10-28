from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.orm import Session

from backend.app.db.models.check_result import CheckResult
from backend.app.db.models.endpoint import MonitoredEndpoint


@pytest.mark.asyncio
async def test_endpoint_metrics_and_history(async_client: httpx.AsyncClient, test_db: Session):
    endpoint = MonitoredEndpoint(name="Search Engine", url="https://api.github.com/status")
    test_db.add(endpoint)
    test_db.commit()

    # Add 10 check results: 9 success, 1 failure
    for i in range(9):
        test_db.add(
            CheckResult(
                endpoint_id=endpoint.id,
                status_code=200,
                response_time_ms=50.0 + (i * 10),
                is_success=True,
                created_at=datetime.now(UTC),
            )
        )
    test_db.add(
        CheckResult(
            endpoint_id=endpoint.id,
            status_code=500,
            response_time_ms=150.0,
            is_success=False,
            error_type="HTTP_ERROR",
            error_message="500 Internal Server Error",
            created_at=datetime.now(UTC),
        )
    )
    test_db.commit()

    # Check metrics
    res = await async_client.get(f"/api/v1/endpoints/{endpoint.id}/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert metrics["total_checks"] == 10
    assert metrics["uptime_percentage"] == 90.0
    assert metrics["avg_latency_ms"] > 0
    assert metrics["p95_latency_ms"] > 0

    # Check history
    hist_res = await async_client.get(f"/api/v1/endpoints/{endpoint.id}/history?page=1&page_size=5")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["total"] == 10
    assert len(hist["items"]) == 5
