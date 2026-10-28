from backend.app.engine.retry import RetryPolicy, calculate_backoff_delay, should_retry_error


def test_retry_policy_defaults():
    policy = RetryPolicy(max_attempts=3, backoff_factor=1.5, jitter=False)
    assert policy.max_attempts == 3
    assert policy.backoff_factor == 1.5


def test_calculate_backoff_delay_exponential():
    policy = RetryPolicy(max_attempts=4, backoff_factor=2.0, jitter=False)
    # attempt 1: 2.0 * (2^0) = 2.0
    # attempt 2: 2.0 * (2^1) = 4.0
    # attempt 3: 2.0 * (2^2) = 8.0
    assert calculate_backoff_delay(attempt=1, policy=policy) == 2.0
    assert calculate_backoff_delay(attempt=2, policy=policy) == 4.0
    assert calculate_backoff_delay(attempt=3, policy=policy) == 8.0


def test_should_retry_transient_vs_permanent():
    # Transient network/server errors -> retry
    assert should_retry_error(error_type="TIMEOUT", status_code=None) is True
    assert should_retry_error(error_type="CONNECTION_REFUSED", status_code=None) is True
    assert should_retry_error(error_type="HTTP_ERROR", status_code=500) is True
    assert should_retry_error(error_type="HTTP_ERROR", status_code=502) is True
    assert should_retry_error(error_type="HTTP_ERROR", status_code=503) is True
    assert should_retry_error(error_type="HTTP_ERROR", status_code=504) is True

    # Permanent client / security errors -> do NOT retry
    assert should_retry_error(error_type="HTTP_ERROR", status_code=400) is False
    assert should_retry_error(error_type="HTTP_ERROR", status_code=401) is False
    assert should_retry_error(error_type="HTTP_ERROR", status_code=403) is False
    assert should_retry_error(error_type="HTTP_ERROR", status_code=404) is False
    assert should_retry_error(error_type="SSRF_BLOCKED", status_code=None) is False
