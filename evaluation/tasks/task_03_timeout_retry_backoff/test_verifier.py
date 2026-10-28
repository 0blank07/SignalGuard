from target import compute_backoff_delay, should_retry


def test_public_timeout_is_retried():
    assert should_retry("TIMEOUT", status_code=None) is True


def test_verifier_never_retry_4xx_client_errors():
    for code in (400, 401, 403, 404, 422):
        assert should_retry("HTTP_ERROR", status_code=code) is False, (
            f"Client error {code} must NOT be retried!"
        )


def test_verifier_retry_5xx_server_errors():
    for code in (500, 502, 503, 504):
        assert should_retry("HTTP_ERROR", status_code=code) is True, (
            f"Server error {code} must be retried!"
        )


def test_verifier_never_retry_ssrf():
    assert should_retry("SSRF_BLOCKED", status_code=None) is False


def test_verifier_backoff_max_delay_cap():
    max_d = 20.0
    # On 10th attempt, unbounded would be 1.0 * 2^9 = 512.0
    delay = compute_backoff_delay(attempt=10, base_delay=1.0, max_delay=max_d, jitter=False)
    assert delay <= max_d, f"Delay {delay} exceeded max_delay cap of {max_d}!"


def test_verifier_jitter_randomness():
    samples = [
        compute_backoff_delay(attempt=3, base_delay=2.0, max_delay=30.0, jitter=True)
        for _ in range(20)
    ]
    # Check that not all samples are identical (jitter must be active)
    assert len(set(samples)) > 1, "Jitter failed to introduce randomness in delay calculation!"
