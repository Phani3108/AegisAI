from __future__ import annotations

from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("aegisai_request_id", default=None)


def set_request_id(v: str | None) -> None:
    _request_id.set(v)


def get_request_id() -> str | None:
    return _request_id.get()
