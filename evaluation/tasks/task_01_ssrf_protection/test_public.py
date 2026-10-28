import pytest
from target import is_url_safe


def test_public_allowed_urls():
    safe, _ = is_url_safe("https://api.github.com/status")
    assert safe is True


def test_public_blocked_schemes():
    safe, reason = is_url_safe("file:///etc/passwd")
    assert safe is False
    assert "scheme" in str(reason).lower()


def test_public_blocked_localhost():
    safe, _ = is_url_safe("http://localhost:8080/metrics")
    assert safe is False
