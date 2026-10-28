import re
from urllib.parse import urlparse

# BUGGY STARTER: Uses naive string checking and incomplete regex
NAIVE_BLOCKED_HOSTS = ["localhost", "127.0.0.1", "169.254.169.254"]


def is_url_safe(url: str, allow_private: bool = False) -> tuple[bool, str | None]:
    if not url:
        return False, "URL cannot be empty"

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL: {e}"

    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported scheme: {parsed.scheme}"

    host = parsed.hostname
    if not host:
        return False, "Missing hostname"

    # Naive check: only checks exact match against simple list
    if host.lower() in NAIVE_BLOCKED_HOSTS:
        return False, f"Host {host} is blocked"

    # Naive regex for private IPs (bypassed by octal, hex, decimal, or DNS)
    if re.match(r"^10\.\d+\.\d+\.\d+$", host):
        return False, "Private IP blocked"

    return True, None
