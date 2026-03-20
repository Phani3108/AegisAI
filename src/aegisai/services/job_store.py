from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from aegisai.schemas.jobs import JobStatusResponse

_jobs: dict[str, JobStatusResponse] = {}
_idempotency: dict[str, str] = {}
_lock = asyncio.Lock()


def utcnow() -> datetime:
    return datetime.now(UTC)


async def set_job(job_id: str, payload: JobStatusResponse) -> None:
    async with _lock:
        _jobs[job_id] = payload


async def patch_job(job_id: str, **updates: Any) -> None:
    async with _lock:
        cur = _jobs[job_id]
        _jobs[job_id] = cur.model_copy(update=updates)


async def get_job(job_id: str) -> JobStatusResponse | None:
    async with _lock:
        return _jobs.get(job_id)


async def idempotency_get(key: str) -> str | None:
    async with _lock:
        return _idempotency.get(key)


async def idempotency_put_if_absent(key: str, job_id: str) -> str | None:
    """Returns existing job_id if key is already mapped; else stores key→job_id and returns None."""
    async with _lock:
        cur = _idempotency.get(key)
        if cur is not None:
            return cur
        _idempotency[key] = job_id
        return None


async def idempotency_delete(key: str) -> None:
    async with _lock:
        _idempotency.pop(key, None)


async def reset_test_state() -> None:
    """Clear in-memory jobs and idempotency (pytest)."""
    async with _lock:
        _jobs.clear()
        _idempotency.clear()

