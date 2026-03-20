"""Optional JSON log lines for stdout (K8s / log aggregators)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from aegisai.services.request_context import get_request_id


class JsonLogFormatter(logging.Formatter):
    """One JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        rid = getattr(record, "request_id", None)
        if not rid:
            rid = get_request_id()
        if rid:
            payload["request_id"] = rid
        return json.dumps(payload, default=str)


def configure_logging(*, json_lines: bool) -> None:
    """Reset root handlers and attach a single StreamHandler to stderr."""
    root = logging.getLogger()
    root.handlers.clear()
    h = logging.StreamHandler(sys.stderr)
    if json_lines:
        h.setFormatter(JsonLogFormatter())
    else:
        h.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"),
        )
    root.addHandler(h)
    root.setLevel(logging.INFO)
