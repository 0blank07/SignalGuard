import ipaddress

import pytest

from backend.app.core.errors import SSRFSecurityException
from backend.app.core.security import (
    is_ip_allowed,
    validate_target_url,
)


def test_allowed_public_url():
    result = validate_target_url("https://api.github.com/status")
    assert result.is_safe is True
    assert result.scheme in ("http", "https")
    assert result.hostname == "api.github.com"
    assert result.port == 443


def test_block_unsupported_schemes():
    for bad_url in [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "gopher://example.com",
        "javascript:alert(1)",
        "data:text/plain;base64,SGVsbG8=",
    ]:
        with pytest.raises(SSRFSecurityException) as exc_info:
            validate_target_url(bad_url)
        assert "scheme" in str(exc_info.value).lower()


def test_block_loopback_and_localhost():
    for bad_url in [
        "http://localhost/",
        "http://localhost:8080/metrics",
        "http://127.0.0.1/",
        "http://127.0.0.1:5432/",
        "http://127.127.127.127/",
        "http://[::1]/",
        "http://[0:0:0:0:0:0:0:1]/",
    ]:
        with pytest.raises(SSRFSecurityException) as exc_info:
            validate_target_url(bad_url)
        assert "blocked" in str(exc_info.value).lower() or "loopback" in str(exc_info.value).lower()


def test_block_private_rfc1918_ips():
    for bad_url in [
        "http://10.0.0.1/admin",
        "http://10.254.0.1/",
        "http://172.16.0.1/",
        "http://172.31.255.255/",
        "http://192.168.1.1/",
        "http://192.168.0.254/",
    ]:
        with pytest.raises(SSRFSecurityException):
            validate_target_url(bad_url)


def test_block_cloud_metadata():
    for bad_url in [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.254/computeMetadata/v1/",
        "http://metadata.google.internal/",
        "http://instance-data/latest/meta-data/",
    ]:
        with pytest.raises(SSRFSecurityException):
            validate_target_url(bad_url)


def test_is_ip_allowed_function():
    assert is_ip_allowed(ipaddress.ip_address("8.8.8.8")) is True
    assert is_ip_allowed(ipaddress.ip_address("1.1.1.1")) is True
    assert is_ip_allowed(ipaddress.ip_address("127.0.0.1")) is False
    assert is_ip_allowed(ipaddress.ip_address("10.0.0.1")) is False
    assert is_ip_allowed(ipaddress.ip_address("169.254.169.254")) is False
    assert is_ip_allowed(ipaddress.ip_address("::1")) is False
    assert is_ip_allowed(ipaddress.ip_address("fc00::1")) is False
