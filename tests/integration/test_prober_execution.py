import httpx
import pytest

from backend.app.db.models.endpoint import MonitoredEndpoint
from backend.app.engine.prober import ProbeExecutionSummary, execute_probe
from backend.app.engine.retry import RetryPolicy


@pytest.mark.asyncio
async def test_prober_success_200():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "healthy"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        endpoint = MonitoredEndpoint(
            id=1,
            name="Test Service",
            url="https://api.example.com/health",
            expected_status=200,
            timeout_seconds=5,
            retry_count=1,
        )
        summary: ProbeExecutionSummary = await execute_probe(
            endpoint=endpoint,
            client=client,
            skip_ssrf=True,  # skip real DNS resolution for mock tests
        )

        assert summary.is_success is True
        assert summary.status_code == 200
        assert summary.error_type is None
        assert summary.response_time_ms > 0
        assert summary.attempts == 1


@pytest.mark.asyncio
async def test_prober_expected_status_mismatch():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        endpoint = MonitoredEndpoint(
            id=2,
            name="404 Service",
            url="https://api.example.com/notfound",
            expected_status=200,
            timeout_seconds=5,
            retry_count=3,
        )
        summary = await execute_probe(endpoint=endpoint, client=client, skip_ssrf=True)

        assert summary.is_success is False
        assert summary.status_code == 404
        assert summary.error_type == "HTTP_ERROR"
        # 404 is not retried
        assert summary.attempts == 1


@pytest.mark.asyncio
async def test_prober_timeout_with_retries():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("Read timed out")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        endpoint = MonitoredEndpoint(
            id=3,
            name="Timeout Service",
            url="https://api.example.com/slow",
            expected_status=200,
            timeout_seconds=1,
            retry_count=3,
        )
        # Pass 0.001 backoff to make unit tests lightning fast
        policy = RetryPolicy(max_attempts=3, backoff_factor=0.001, jitter=False)
        summary = await execute_probe(
            endpoint=endpoint,
            client=client,
            retry_policy=policy,
            skip_ssrf=True,
        )

        assert summary.is_success is False
        assert summary.error_type == "TIMEOUT"
        assert summary.attempts == 3
        assert attempts == 3


@pytest.mark.asyncio
async def test_prober_ssrf_blocked_url():
    endpoint = MonitoredEndpoint(
        id=4,
        name="Malicious Target",
        url="http://127.0.0.1:8080/secret",
        expected_status=200,
        timeout_seconds=5,
        retry_count=3,
    )
    summary = await execute_probe(endpoint=endpoint, skip_ssrf=False)

    assert summary.is_success is False
    assert summary.error_type == "SSRF_BLOCKED"
    assert summary.attempts == 1  # SSRF is never retried
