from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from aegisai.schemas.jobs import JobStatusResponse

_jobs: dict[str, JobStatusResponse] = {}
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

