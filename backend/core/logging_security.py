"""Best-effort redaction of credentials from application logs."""

from __future__ import annotations

import logging
import re

_SENSITIVE = re.compile(
    r"(?i)(apikey|api[_-]?key|authorization|password|token|jwt_secret)"
    r"([\s:=\"']+)([^\s&\"']+)"
)
_DATABASE_URL = re.compile(r"(?i)(postgres(?:ql)?://[^:\s/]+:)([^@\s]+)(@)")


def redact_secrets(message: str) -> str:
    message = _SENSITIVE.sub(r"\1\2[REDACTED]", message)
    return _DATABASE_URL.sub(r"\1[REDACTED]\3", message)


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secrets(record.getMessage())
        record.args = ()
        return True


def install_secret_redaction() -> None:
    redactor = SecretRedactionFilter()
    roots = (logging.getLogger(), logging.getLogger("uvicorn"))
    for root in roots:
        for handler in root.handlers:
            if not any(
                isinstance(item, SecretRedactionFilter) for item in handler.filters
            ):
                handler.addFilter(redactor)
