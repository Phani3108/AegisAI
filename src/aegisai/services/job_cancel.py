"""Best-effort cooperative cancellation for async pipeline jobs."""

from __future__ import annotations

import asyncio

from aegisai.services.redis_util import get_redis_client

_requested: set[str] = set()
_lock = asyncio.Lock()
_KEY_PREFIX = "aegisai:cancel:"


async def request_cancel(job_id: str) -> None:
    r = get_redis_client()
    if r is not None:
        await r.set(_KEY_PREFIX + job_id, "1", ex=3600)
        return
    async with _lock:
        _requested.add(job_id)


async def is_requested(job_id: str) -> bool:
    r = get_redis_client()
    if r is not None:
        v = await r.get(_KEY_PREFIX + job_id)
        return v is not None
    async with _lock:
        return job_id in _requested


async def clear(job_id: str) -> None:
    r = get_redis_client()
    if r is not None:
        await r.delete(_KEY_PREFIX + job_id)
        return
    async with _lock:
        _requested.discard(job_id)


async def reset_for_tests() -> None:
    async with _lock:
        _requested.clear()
