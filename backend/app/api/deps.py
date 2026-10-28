from fastapi import Header

from backend.app.config import get_settings
from backend.app.core.errors import AuthenticationError


def verify_api_key(
    x_signalguard_api_key: str | None = Header(default=None),
) -> str | None:
    settings = get_settings()
    if not settings.REQUIRE_API_KEY:
        return x_signalguard_api_key

    if not x_signalguard_api_key or x_signalguard_api_key != settings.API_KEY:
        raise AuthenticationError("Invalid or missing API key header.")

    return x_signalguard_api_key
