import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
]

BLOCKED_IPV6_NETWORKS = [
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

METADATA_HOSTNAMES = {"169.254.169.254", "metadata.google.internal", "instance-data", "localhost"}


def try_parse_numeric_or_obfuscated_ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    clean = hostname.strip("[]")
    try:
        return ipaddress.ip_address(clean)
    except ValueError:
        pass

    if clean.isdigit():
        try:
            num = int(clean)
            if 0 <= num <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(num)
        except (ValueError, OverflowError):
            pass

    if clean.lower().startswith("0x"):
        try:
            num = int(clean, 16)
            if 0 <= num <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(num)
        except (ValueError, OverflowError):
            pass

    parts = clean.split(".")
    if 1 <= len(parts) <= 4:
        try:
            parsed = []
            for p in parts:
                if p.lower().startswith("0x"):
                    parsed.append(int(p, 16))
                elif p.startswith("0") and len(p) > 1 and p.isdigit():
                    parsed.append(int(p, 8))
                elif p.isdigit():
                    parsed.append(int(p, 10))
                else:
                    return None
            if len(parsed) == 4 and all(0 <= v <= 255 for v in parsed):
                return ipaddress.IPv4Address(bytes(parsed))
            elif len(parsed) == 2 and 0 <= parsed[0] <= 255 and 0 <= parsed[1] <= 0xFFFFFF:
                return ipaddress.IPv4Address((parsed[0] << 24) | parsed[1])
            elif len(parsed) == 1 and 0 <= parsed[0] <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(parsed[0])
        except (ValueError, OverflowError):
            pass

    return None


def is_ip_safe(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, allow_private: bool = False) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if allow_private:
        return not (ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved)

    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return False

    if isinstance(ip, ipaddress.IPv4Address):
        for net in BLOCKED_NETWORKS:
            if ip in net:
                return False
    elif isinstance(ip, ipaddress.IPv6Address):
        for net in BLOCKED_IPV6_NETWORKS:
            if ip in net:
                return False

    return True


def is_url_safe(url: str, allow_private: bool = False) -> tuple[bool, str | None]:
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported scheme: {parsed.scheme}"

    host = parsed.hostname
    if not host:
        return False, "Missing hostname"

    if host.lower() in METADATA_HOSTNAMES:
        return False, f"Blocked metadata or localhost host: {host}"

    literal = try_parse_numeric_or_obfuscated_ip(host)
    if literal is not None:
        if not is_ip_safe(literal, allow_private=allow_private):
            return False, f"Blocked IP address: {literal}"
        return True, None

    try:
        addrs = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        return False, f"DNS resolution failed: {e}"

    if not addrs:
        return False, "DNS returned zero addresses"

    for entry in addrs:
        ip_str = entry[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if not is_ip_safe(ip, allow_private=allow_private):
                return False, f"Resolved IP {ip} is in a blocked network range"
        except ValueError:
            continue

    return True, None
