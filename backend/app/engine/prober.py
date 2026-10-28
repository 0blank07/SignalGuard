import asyncio
import time
from dataclasses import dataclass

import httpx

from backend.app.config import get_settings
from backend.app.core.errors import SSRFSecurityException
from backend.app.core.security import validate_target_url
from backend.app.db.models.endpoint import MonitoredEndpoint
from backend.app.engine.retry import RetryPolicy, calculate_backoff_delay, should_retry_error


@dataclass
class ProbeExecutionSummary:
    endpoint_id: int
    url: str
    is_success: bool
    status_code: int | None
    response_time_ms: float
    error_type: str | None
    error_message: str | None
    response_snippet: str | None
    attempts: int


async def execute_probe(
    endpoint: MonitoredEndpoint,
    client: httpx.AsyncClient | None = None,
    retry_policy: RetryPolicy | None = None,
    skip_ssrf: bool = False,
) -> ProbeExecutionSummary:
    """Executes an asynchronous HTTP probe against a monitored endpoint with bounded retries."""
    settings = get_settings()

    if retry_policy is None:
        retry_policy = RetryPolicy(
            max_attempts=endpoint.retry_count if endpoint.retry_count > 0 else 1,
            backoff_factor=settings.RETRY_BACKOFF_FACTOR,
            jitter=True,
        )

    # 1. Pre-flight SSRF Validation
    if not skip_ssrf:
        try:
            validate_target_url(endpoint.url, allow_private=settings.ALLOW_PRIVATE_IPS)
        except SSRFSecurityException as ssrf_err:
            return ProbeExecutionSummary(
                endpoint_id=endpoint.id,
                url=endpoint.url,
                is_success=False,
                status_code=None,
                response_time_ms=0.0,
                error_type="SSRF_BLOCKED",
                error_message=str(ssrf_err),
                response_snippet=None,
                attempts=1,
            )

    attempts = 0
    last_error_type: str | None = None
    last_error_message: str | None = None
    last_status_code: int | None = None
    last_snippet: str | None = None
    total_latency_ms = 0.0

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(
            follow_redirects=False,  # redirects are checked manually to prevent SSRF bypass
            verify=True,
        )
        owns_client = True

    try:
        while attempts < retry_policy.max_attempts:
            attempts += 1
            t_start = time.perf_counter()

            try:
                # Prepare request payload & headers
                headers = dict(endpoint.headers or {})
                headers.setdefault("User-Agent", f"SignalGuard-Prober/{settings.VERSION}")
                method = (endpoint.method or "GET").upper()
                timeout_val = float(endpoint.timeout_seconds if endpoint.timeout_seconds else settings.DEFAULT_TIMEOUT_SECONDS)

                response = await client.request(
                    method=method,
                    url=endpoint.url,
                    headers=headers,
                    content=endpoint.body.encode("utf-8") if endpoint.body else None,
                    timeout=timeout_val,
                )
                latency_ms = (time.perf_counter() - t_start) * 1000.0
                total_latency_ms = latency_ms
                last_status_code = response.status_code

                # Read safely bounded snippet (max 16KB)
                content_bytes = response.content[:settings.MAX_BODY_PREVIEW_BYTES]
                last_snippet = content_bytes.decode("utf-8", errors="replace")

                # Validate status code against expected status
                if response.status_code == endpoint.expected_status:
                    return ProbeExecutionSummary(
                        endpoint_id=endpoint.id,
                        url=endpoint.url,
                        is_success=True,
                        status_code=response.status_code,
                        response_time_ms=round(latency_ms, 2),
                        error_type=None,
                        error_message=None,
                        response_snippet=last_snippet,
                        attempts=attempts,
                    )
                else:
                    last_error_type = "HTTP_ERROR"
                    last_error_message = (
                        f"Expected status {endpoint.expected_status}, received {response.status_code}"
                    )

            except httpx.TimeoutException as ex:
                latency_ms = (time.perf_counter() - t_start) * 1000.0
                total_latency_ms = latency_ms
                last_error_type = "TIMEOUT"
                last_error_message = f"Request timed out after {endpoint.timeout_seconds}s: {ex}"

            except httpx.ConnectError as ex:
                latency_ms = (time.perf_counter() - t_start) * 1000.0
                total_latency_ms = latency_ms
                err_str = str(ex).lower()
                if "getaddrinfo" in err_str or "name resolution" in err_str:
                    last_error_type = "DNS_ERROR"
                else:
                    last_error_type = "CONNECTION_REFUSED"
                last_error_message = f"Connection failed: {ex}"

            except Exception as ex:
                latency_ms = (time.perf_counter() - t_start) * 1000.0
                total_latency_ms = latency_ms
                last_error_type = "NETWORK_ERROR"
                last_error_message = f"Probe encountered unexpected error: {ex}"

            # Check if this error is retryable
            if attempts < retry_policy.max_attempts and should_retry_error(
                last_error_type, last_status_code
            ):
                delay = calculate_backoff_delay(attempts, retry_policy)
                await asyncio.sleep(delay)
            else:
                break

    finally:
        if owns_client:
            await client.aclose()

    return ProbeExecutionSummary(
        endpoint_id=endpoint.id,
        url=endpoint.url,
        is_success=False,
        status_code=last_status_code,
        response_time_ms=round(total_latency_ms, 2),
        error_type=last_error_type,
        error_message=last_error_message,
        response_snippet=last_snippet,
        attempts=attempts,
    )
