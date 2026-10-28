import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse
from backend.app.core.errors import SSRFSecurityException

# Cloud metadata addresses and hostnames
CLOUD_METADATA_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "instance-data",
}

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (local broadcast)
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (Carrier-grade NAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local (including cloud metadata)
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
    ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved / Future use
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
]

BLOCKED_IPV6_NETWORKS = [
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),           # Loopback
    ipaddress.ip_network("100::/64"),          # Discard-only
    ipaddress.ip_network("2001:db8::/32"),     # Documentation
    ipaddress.ip_network("fc00::/7"),          # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),         # Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),          # Multicast
]


@dataclass(frozen=True)
class ParsedURLValidationResult:
    is_safe: bool
    url: str
    scheme: str
    hostname: str
    port: int
    resolved_ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address]


def unwrap_ipv4_mapped(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Unwraps IPv4-mapped IPv6 address (e.g., ::ffff:127.0.0.1 -> 127.0.0.1)."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return ip.ipv4_mapped
    return ip


def is_ip_allowed(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    allow_private: bool = False,
) -> bool:
    """Evaluates whether an IP address is permissible for outbound monitoring requests."""
    ip = unwrap_ipv4_mapped(ip)

    if allow_private:
        # Even if allow_private is true, never allow loopback or link-local/cloud metadata
        if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False
        return True

    # Standard production security checks:
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False

    # Check IPv4 blocklists explicitly
    if isinstance(ip, ipaddress.IPv4Address):
        for network in BLOCKED_IP_NETWORKS:
            if ip in network:
                return False

    # Check IPv6 blocklists explicitly
    if isinstance(ip, ipaddress.IPv6Address):
        for network in BLOCKED_IPV6_NETWORKS:
            if ip in network:
                return False

    return True


def try_parse_numeric_or_obfuscated_ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Tries parsing decimal, octal, hex, or dotted numeric variations into an IP address."""
    clean_host = hostname.strip("[]")

    # Direct standard parse
    try:
        return ipaddress.ip_address(clean_host)
    except ValueError:
        pass

    # Decimal integer format (e.g., 2130706433)
    if clean_host.isdigit():
        try:
            num = int(clean_host)
            if 0 <= num <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(num)
        except (ValueError, OverflowError):
            pass

    # Hex integer format (e.g., 0x7f000001)
    if clean_host.lower().startswith("0x"):
        try:
            num = int(clean_host, 16)
            if 0 <= num <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(num)
        except (ValueError, OverflowError):
            pass

    # Dotted octal or mixed hex parts (e.g., 0177.0.0.1 or 0x7f.0.0.1)
    parts = clean_host.split(".")
    if 1 <= len(parts) <= 4:
        try:
            parsed_parts: list[int] = []
            for p in parts:
                if p.lower().startswith("0x"):
                    val = int(p, 16)
                elif p.startswith("0") and len(p) > 1 and p.isdigit():
                    val = int(p, 8)
                elif p.isdigit():
                    val = int(p, 10)
                else:
                    return None
                parsed_parts.append(val)

            # Reconstruct IPv4 number according to standard POSIX inet_aton behavior
            if len(parsed_parts) == 4:
                if all(0 <= v <= 255 for v in parsed_parts):
                    return ipaddress.IPv4Address(bytes(parsed_parts))
            elif len(parsed_parts) == 2:
                # e.g., 127.1 -> 127.0.0.1
                if 0 <= parsed_parts[0] <= 255 and 0 <= parsed_parts[1] <= 0xFFFFFF:
                    ip_int = (parsed_parts[0] << 24) | parsed_parts[1]
                    return ipaddress.IPv4Address(ip_int)
            elif len(parsed_parts) == 1:
                if 0 <= parsed_parts[0] <= 0xFFFFFFFF:
                    return ipaddress.IPv4Address(parsed_parts[0])
        except (ValueError, OverflowError):
            pass

    return None


def resolve_and_verify_ip(
    hostname: str,
    allow_private: bool = False,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolves a hostname via DNS and verifies that all resolved IP addresses are public."""
    # Check if host is numeric/literal IP
    literal_ip = try_parse_numeric_or_obfuscated_ip(hostname)
    if literal_ip is not None:
        if not is_ip_allowed(literal_ip, allow_private=allow_private):
            raise SSRFSecurityException(
                f"Target IP address '{literal_ip}' is in a blocked or private network range.",
                details={"ip": str(literal_ip), "blocked_type": "PRIVATE_OR_RESERVED"},
            )
        return [literal_ip]

    # Check for known metadata and local hostnames
    if hostname.lower() in CLOUD_METADATA_HOSTS or hostname.lower() in ("localhost", "localhost.localdomain"):
        raise SSRFSecurityException(
            f"Target hostname '{hostname}' is blocked (local or cloud metadata destination).",
            details={"hostname": hostname, "blocked_type": "METADATA_OR_LOCAL"},
        )

    # Perform DNS resolution
    try:
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise SSRFSecurityException(
            f"DNS resolution failed for hostname '{hostname}': {e}",
            details={"hostname": hostname, "error": str(e)},
        )

    resolved_ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if not is_ip_allowed(ip, allow_private=allow_private):
                raise SSRFSecurityException(
                    f"Resolved IP '{ip}' for hostname '{hostname}' is blocked.",
                    details={"hostname": hostname, "resolved_ip": str(ip)},
                )
            resolved_ips.append(ip)
        except ValueError:
            continue

    if not resolved_ips:
        raise SSRFSecurityException(
            f"No valid IP addresses resolved for hostname '{hostname}'",
            details={"hostname": hostname},
        )

    return resolved_ips


def validate_target_url(
    url: str,
    allow_private: bool = False,
) -> ParsedURLValidationResult:
    """Validates target URL scheme, hostname, and resolves IPs to guarantee SSRF protection."""
    if not url or not isinstance(url, str):
        raise SSRFSecurityException("URL must be a non-empty string.")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise SSRFSecurityException(f"Failed to parse URL '{url}': {e}")

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise SSRFSecurityException(
            f"Unsupported scheme '{scheme}'. Only HTTP and HTTPS are permitted.",
            details={"scheme": scheme},
        )

    # Handle userinfo: parsed.hostname correctly strips username:password@
    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityException(
            "URL is missing a valid hostname.",
            details={"url": url},
        )

    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80

    resolved_ips = resolve_and_verify_ip(hostname, allow_private=allow_private)

    return ParsedURLValidationResult(
        is_safe=True,
        url=url,
        scheme=scheme,
        hostname=hostname,
        port=port,
        resolved_ips=resolved_ips,
    )
