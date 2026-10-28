import logging

import pytest

from backend.app.config import Settings
from backend.app.core.errors import (
    ConflictError,
    NotFoundError,
    SSRFSecurityException,
    ValidationError,
)
from backend.app.core.logging import RedactingFormatter


def test_settings_default_values():
    settings = Settings(
        DATABASE_URL="sqlite:///./test.db",
        ENVIRONMENT="test",
        SECRET_KEY="test-secret-key-at-least-32-chars-long",
    )
    assert settings.DATABASE_URL == "sqlite:///./test.db"
    assert settings.ENVIRONMENT == "test"
    assert settings.MAX_CONCURRENT_CHECKS == 50
    assert settings.DEFAULT_CHECK_INTERVAL_SECONDS == 30
    assert settings.DEFAULT_TIMEOUT_SECONDS == 10
    assert settings.MIN_CHECK_INTERVAL_SECONDS == 5
    assert settings.MAX_TIMEOUT_SECONDS == 60


def test_settings_validation_invalid_interval():
    with pytest.raises(Exception):
        Settings(
            DATABASE_URL="sqlite:///./test.db",
            DEFAULT_CHECK_INTERVAL_SECONDS=1,  # below minimum of 5 seconds
        )


def test_app_exceptions_hierarchy():
    nf = NotFoundError("Endpoint", 42)
    assert nf.status_code == 404
    assert "Endpoint" in nf.message
    assert nf.to_dict()["code"] == "NOT_FOUND"

    ve = ValidationError("Invalid URL provided", details={"url": "not a url"})
    assert ve.status_code == 422
    assert ve.to_dict()["code"] == "VALIDATION_ERROR"

    ce = ConflictError("Incident already open")
    assert ce.status_code == 409
    assert ce.to_dict()["code"] == "CONFLICT"

    ssrf = SSRFSecurityException("Blocked loopback IP: 127.0.0.1")
    assert ssrf.status_code == 400
    assert ssrf.to_dict()["code"] == "SSRF_BLOCKED"


def test_redacting_formatter():
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Bearer eyJhbGciOiJIUzI1NiJ9.secret and Authorization: Bearer token123 and password=SuperSecretPassword!",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "SuperSecretPassword!" not in formatted
    assert "[REDACTED]" in formatted
