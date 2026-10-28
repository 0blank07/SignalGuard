# Explanation: SSRF Vulnerability & Mitigation

## Vulnerability Analysis

The starter implementation suffered from the classic **SSRF Naive Blocklist Anti-Pattern**:
1. It inspected the raw hostname string using regex or `hostname in ["localhost", "127.0.0.1"]`.
2. It failed to account for alternative numeric bases parsed by POSIX `inet_aton` (octal `0177.0.0.1`, hex `0x7f000001`, raw decimal integer `2130706433`).
3. It failed to resolve DNS hostnames to actual IP addresses prior to connecting, enabling DNS rebinding attacks.
4. It ignored IPv6 loopback (`::1`) and IPv4-mapped IPv6 loopbacks (`::ffff:127.0.0.1`).

## Impact

An attacker could submit internal service URLs (e.g. `http://169.254.169.254/latest/meta-data/identity-credentials/`) to extract production cloud tokens, or target internal databases (`http://10.0.0.5:5432`) to map VPC network architecture.

## Resolution

1. Use standard `urllib.parse.urlsplit` to isolate scheme, hostname, and credentials.
2. Enforce scheme strictly in `("http", "https")`.
3. Normalize and unwrap IPv4-mapped IPv6 addresses (`ip.ipv4_mapped`).
4. Parse numeric encodings (octal, hex, decimal) into canonical `ipaddress.IPv4Address`.
5. Resolve hostnames through DNS using `socket.getaddrinfo` and verify that *all* returned socket addresses belong exclusively to public, routable IP ranges.
