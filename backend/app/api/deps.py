from collections.abc import Generator
from fastapi import Header, HTTPException, Security, status
from sqlalchemy.orm import Session
from backend.app.config import get_settings
from backend.app.core.errors import AuthenticationError
from backend.app.db.session import get_db


def verify_api_key(
    x_signalguard_api_key: str | None = Header(default=None),
) -> str | None:
    settings = get_settings()
    if not settings.REQUIRE_API_KEY:
        return x_signalguard_api_key

    if not x_signalguard_api_key or x_signalguard_api_key != settings.API_KEY:
        raise AuthenticationError("Invalid or missing API key header.")

    return x_signalguard_api_key
