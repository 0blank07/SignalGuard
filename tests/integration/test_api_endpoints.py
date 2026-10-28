import httpx
import pytest


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: httpx.AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_create_endpoint_success(async_client: httpx.AsyncClient):
    payload = {
        "name": "Public API Health",
        "url": "https://api.github.com/status",
        "method": "GET",
        "interval_seconds": 30,
        "timeout_seconds": 5,
        "expected_status": 200,
    }
    response = await async_client.post("/api/v1/endpoints", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Public API Health"
    assert data["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_create_endpoint_ssrf_rejection(async_client: httpx.AsyncClient):
    payload = {
        "name": "Local Attack",
        "url": "http://127.0.0.1:8080/metrics",
        "method": "GET",
    }
    response = await async_client.post("/api/v1/endpoints", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "SSRF" in data["error"]["code"] or "blocked" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_list_and_filter_endpoints(async_client: httpx.AsyncClient):
    # Create two endpoints
    await async_client.post(
        "/api/v1/endpoints",
        json={"name": "Service A", "url": "https://api.github.com/status"},
    )
    await async_client.post(
        "/api/v1/endpoints",
        json={"name": "Service B", "url": "https://api.github.com/octocat"},
    )

    response = await async_client.get("/api/v1/endpoints?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_pause_and_resume_endpoint(async_client: httpx.AsyncClient):
    create_res = await async_client.post(
        "/api/v1/endpoints",
        json={"name": "Pausable Service", "url": "https://api.github.com/status"},
    )
    eid = create_res.json()["id"]

    # Pause
    pause_res = await async_client.post(f"/api/v1/endpoints/{eid}/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    # Resume
    resume_res = await async_client.post(f"/api/v1/endpoints/{eid}/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] != "PAUSED"
