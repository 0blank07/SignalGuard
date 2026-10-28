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


def test_verifier_decimal_ip_bypass():
    # 2130706433 == 127.0.0.1
    safe, _ = is_url_safe("http://2130706433/admin")
    assert safe is False, "Failed to block decimal encoded IP (127.0.0.1)"


def test_verifier_octal_ip_bypass():
    # 0177.0.0.1 == 127.0.0.1
    safe, _ = is_url_safe("http://0177.0.0.1/status")
    assert safe is False, "Failed to block octal encoded IP (127.0.0.1)"


def test_verifier_hex_ip_bypass():
    # 0x7f000001 == 127.0.0.1
    safe, _ = is_url_safe("http://0x7f000001/status")
    assert safe is False, "Failed to block hex encoded IP"


def test_verifier_userinfo_spoof():
    safe, _ = is_url_safe("http://trusted.com@127.0.0.1/keys")
    assert safe is False, "Failed to block userinfo spoofed loopback address"


def test_verifier_ipv6_mapped_loopback():
    safe, _ = is_url_safe("http://[::ffff:127.0.0.1]/")
    assert safe is False, "Failed to block IPv4-mapped IPv6 loopback"


def test_verifier_link_local_ipv6():
    safe, _ = is_url_safe("http://[fe80::1]/")
    assert safe is False, "Failed to block IPv6 link-local address"


def test_verifier_public_ip_allowed():
    safe, _ = is_url_safe("http://8.8.8.8/")
    assert safe is True, "Public IP 8.8.8.8 should be permitted"
