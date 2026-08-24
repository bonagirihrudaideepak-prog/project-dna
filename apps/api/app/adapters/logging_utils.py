"""Structured logging and app-wide logger setup.

Emits JSON lines with level, timestamp, logger, message, and optional extra
fields. Fall back to plain text lines if JSON serialization fails.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            payload["exc"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        try:
            return json.dumps(payload, default=str)
        except (TypeError, ValueError):
            return record.getMessage()


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


def new_request_id() -> str:
    return uuid.uuid4().hex


def log_with_context(logger: logging.Logger, level: int, message: str, **context: Any) -> None:
    logger.log(level, message, extra={"extra_fields": context})
