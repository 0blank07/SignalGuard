import random
from dataclasses import dataclass


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_factor: float = 1.5
    jitter: bool = True
    max_delay_seconds: float = 30.0


def calculate_backoff_delay(attempt: int, policy: RetryPolicy) -> float:
    """Calculates exponential backoff delay with optional random jitter.

    attempt: 1-based attempt index (1, 2, 3...)
    delay = backoff_factor * (2 ** (attempt - 1))
    """
    base_delay = policy.backoff_factor * (2.0 ** max(0, attempt - 1))
    delay = min(base_delay, policy.max_delay_seconds)
    if policy.jitter:
        # Full jitter between 0 and calculated delay
        delay = random.uniform(0.5 * delay, delay)
    return delay


def should_retry_error(error_type: str | None, status_code: int | None) -> bool:
    """Determines whether an error condition represents a transient failure worth retrying.

    Permanent errors (4xx client errors, SSRF blocks, malformed schema) MUST NOT be retried.
    Transient errors (timeouts, connection resets, DNS blips, 500, 502, 503, 504) SHOULD be retried.
    """
    if error_type == "SSRF_BLOCKED":
        return False

    if error_type in ("TIMEOUT", "CONNECTION_REFUSED", "DNS_ERROR"):
        return True

    if error_type == "HTTP_ERROR" and status_code is not None:
        # 5xx are transient server errors
        if status_code >= 500:
            return True
        # 4xx are permanent client/contract errors
        return False

    return False
