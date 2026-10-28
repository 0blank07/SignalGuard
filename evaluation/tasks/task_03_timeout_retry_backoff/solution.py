import random


def should_retry(error_type: str, status_code: int | None) -> bool:
    if error_type in ("SSRF_BLOCKED", "INVALID_PAYLOAD"):
        return False

    if error_type in ("TIMEOUT", "CONNECTION_ERROR", "DNS_ERROR"):
        return True

    if error_type == "HTTP_ERROR" and status_code is not None:
        # Only retry 5xx transient server errors
        if status_code >= 500:
            return True
        # 4xx client errors are permanent
        return False

    return False


def compute_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> float:
    attempt_idx = max(0, attempt - 1)
    delay = min(base_delay * (2.0 ** attempt_idx), max_delay)

    if jitter:
        delay = random.uniform(0.5 * delay, delay)

    return round(delay, 4)
