"""Optional shared Redis client for distributed idempotency and rate limiting."""

from __future__ import annotations

from typing import Any

_client: Any = None


def set_redis_client(client: Any | None) -> None:
    global _client
    _client = client


def get_redis_client() -> Any | None:
    return _client
