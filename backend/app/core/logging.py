import logging
import re
import sys
from typing import Any


SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|secret|token|api[_-]?key|authorization)[=\s:]+([^\s&,;]+)"),
    re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]+)"),
]


class RedactingFormatter(logging.Formatter):
    """Logs formatter that redacts bearer tokens, credentials, and api keys."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = original
        for pattern in SENSITIVE_PATTERNS:
            redacted = pattern.sub(r"\1 [REDACTED]", redacted)
        return redacted


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    formatter = RedactingFormatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
