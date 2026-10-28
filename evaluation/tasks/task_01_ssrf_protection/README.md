# Task 01: SSRF Defense and Hostname Validation

## Problem Statement

SignalGuard allows users to register target URLs for automated uptime monitoring. A vulnerable validation routine (`is_url_safe(url)`) currently uses basic regex and hostname string checking.

Security testing discovered multiple bypass techniques:
1. **Octal and Hex IP encodings:** An attacker registers `http://0177.0.0.1` or `http://0x7f000001` or decimal `http://2130706433` which points to `127.0.0.1` (loopback).
2. **Cloud Metadata IP:** Link-local addresses like `http://169.254.169.254/latest/meta-data/` expose AWS/GCP IAM credentials.
3. **URL Userinfo Tricks:** `http://trusted.com@127.0.0.1/` tricks naive regex checking for `trusted.com`.
4. **IPv6 Mapped & ULA:** `http://[::ffff:127.0.0.1]/` and `http://[fe80::1]/`.
5. **Non-HTTP Schemes:** URLs with `file:///etc/passwd`, `gopher://`, or `ftp://`.

## Requirements

Implement `is_url_safe(url: str, allow_private: bool = False) -> tuple[bool, str | None]` in `target.py`:
- Return `(True, None)` for legitimate public URLs (e.g. `https://api.github.com/status`, `http://8.8.8.8`).
- Return `(False, "<reason>")` for any forbidden URL:
  - Non-HTTP/HTTPS schemes
  - Missing hostname
  - Loopback (`127.0.0.0/8`, `::1`)
  - RFC 1918 Private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
  - Link-Local and Cloud Metadata (`169.254.0.0/16`, `fe80::/10`)
  - Carrier-grade NAT (`100.64.0.0/10`)
  - Multicast and Reserved blocks
- Resolve hostnames via DNS and check *every* resolved IP address.
