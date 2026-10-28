# BUGGY STARTER: Retries 4xx errors, unbounded exponential, missing jitter

def should_retry(error_type: str, status_code: int | None) -> bool:
    # BUG: Retries all HTTP errors indiscriminately, including 404 and 401!
    if error_type == "HTTP_ERROR":
        return True
    if error_type in ("TIMEOUT", "CONNECTION_ERROR"):
        return True
    return False


def compute_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> float:
    # BUG: Unbounded delay: 10th attempt delay = 1.0 * (2 ** 10) = 1024.0s (ignores max_delay!)
    # BUG: Completely ignores jitter flag!
    return base_delay * (2.0 ** attempt)
