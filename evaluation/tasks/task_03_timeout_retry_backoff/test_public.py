import pytest
from target import should_retry, compute_backoff_delay


def test_public_timeout_is_retried():
    assert should_retry("TIMEOUT", status_code=None) is True


def test_public_backoff_increases():
    d1 = compute_backoff_delay(1, base_delay=1.0, jitter=False)
    d2 = compute_backoff_delay(2, base_delay=1.0, jitter=False)
    assert d2 > d1
