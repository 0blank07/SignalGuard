# Task 03: Bounded Retry Policy & Error Classification

## Problem Statement

A resilient prober must retry transient failures (502 Bad Gateway, 503 Service Unavailable, network timeouts) to prevent spurious alerts. However, retrying deterministic errors (401 Unauthorized, 404 Not Found, 400 Bad Request) wastes server resources and delays reporting.

The starter implementation in `target.py` has three critical flaws:
1. **Retries Deterministic 4xx Responses:** It treats HTTP 404 and 401 as retryable, retrying them repeatedly before finally failing.
2. **Unbounded Exponential Delay:** Delay calculation `backoff ** attempt` grows without limit (e.g. attempting 10 retries causes delays of hours or floating point overflow).
3. **Missing Jitter:** Retries fire at deterministic intervals, creating thundering herds when multiple monitors retry simultaneously.

## Requirements

Implement in `target.py`:
- `should_retry(error_type: str, status_code: int | None) -> bool`:
  - Returns `True` for transient errors: `"TIMEOUT"`, `"CONNECTION_ERROR"`, `"DNS_ERROR"`, and HTTP `5xx` (500, 502, 503, 504).
  - Returns `False` for permanent errors: HTTP `4xx` (400, 401, 403, 404), `"SSRF_BLOCKED"`, `"INVALID_PAYLOAD"`.
- `compute_backoff_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0, jitter: bool = True) -> float`:
  - `attempt` is 1-based (1, 2, 3...).
  - Calculates `min(base_delay * (2 ** (attempt - 1)), max_delay)`.
  - When `jitter=True`, randomly perturbs delay between `0.5 * delay` and `delay`.
  - Never returns a delay exceeding `max_delay` or less than 0.
