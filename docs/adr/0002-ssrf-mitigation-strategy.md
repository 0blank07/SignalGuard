# ADR 0002: Comprehensive SSRF Mitigation & DNS Verification

## Status
Accepted

## Context
SignalGuard probes arbitrary target URLs supplied by users. This exposes the host infrastructure to Server-Side Request Forgery (SSRF), specifically targeting cloud provider metadata endpoints (`169.254.169.254`), loopback services (`127.0.0.1`), and internal RFC 1918 subnets (`10.0.0.0/8`). Attackers frequently attempt evasion via octal/hex IP notation and DNS rebinding.

## Decision
We enforce a multi-layered defense:
1. URL parsing via `urllib.parse` with strict scheme filtering (`http` and `https` only).
2. Explicit normalization and parsing of obfuscated IP literals (decimal, octal, hex, and IPv4-mapped IPv6).
3. Pre-flight DNS resolution checking all resolved IP addresses against blocklists (`is_loopback`, `is_private`, `is_link_local`, `is_reserved`, `is_multicast`).
4. Disabling automatic redirect following in the HTTP prober to prevent redirect-based SSRF bypasses.

## Consequences
- **Positive:** Immune to standard and obfuscated SSRF attacks, cloud metadata exfiltration, and local port scanning.
- **Trade-off:** Target hostnames must be resolvable via DNS at registration time. A mock flag is provided for offline unit test environments.
