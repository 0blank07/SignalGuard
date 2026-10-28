import pytest

from backend.app.core.errors import SSRFSecurityException
from backend.app.core.security import validate_target_url


def test_obfuscated_ip_representations():
    evasion_attempts = [
        "http://2130706433/",            # 127.0.0.1 in decimal integer
        "http://0x7f000001/",            # 127.0.0.1 in hex integer
        "http://0177.0.0.1/",            # 127.0.0.1 with octal leading zero
        "http://0x7f.0.0.1/",            # 127.0.0.1 with mixed hex
        "http://0/",                     # 0.0.0.0 in decimal integer
        "http://0.0.0.0/",               # 0.0.0.0 standard
        "http://127.1/",                 # Shorthand 127.0.0.1
    ]
    for url in evasion_attempts:
        with pytest.raises(SSRFSecurityException):
            validate_target_url(url)


def test_userinfo_spoofing():
    # Attacker tries http://google.com@127.0.0.1/ to trick naive host parsers
    spoofed_urls = [
        "http://google.com@127.0.0.1/",
        "http://legit-domain.com:password@169.254.169.254/latest/meta-data/",
    ]
    for url in spoofed_urls:
        with pytest.raises(SSRFSecurityException):
            validate_target_url(url)


def test_ipv6_scoped_and_mapped_addresses():
    ipv6_attacks = [
        "http://[::ffff:127.0.0.1]/",        # IPv4-mapped IPv6 loopback
        "http://[::ffff:10.0.0.1]/",         # IPv4-mapped private
        "http://[::ffff:169.254.169.254]/",  # IPv4-mapped metadata
        "http://[fe80::1]/",                 # IPv6 link-local
    ]
    for url in ipv6_attacks:
        with pytest.raises(SSRFSecurityException):
            validate_target_url(url)
