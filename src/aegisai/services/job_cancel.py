"""Best-effort cooperative cancellation for async pipeline jobs."""

from __future__ import annotations

import asyncio

_requested: set[str] = set()
_lock = asyncio.Lock()


async def request_cancel(job_id: str) -> None:
    async with _lock:
        _requested.add(job_id)


async def is_requested(job_id: str) -> bool:
    async with _lock:
        return job_id in _requested


async def clear(job_id: str) -> None:
    async with _lock:
        _requested.discard(job_id)


async def reset_for_tests() -> None:
    async with _lock:
        _requested.clear()
