from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aegisai.config import get_settings
from aegisai.schemas.jobs import JobRequest, JobStatus, JobStatusResponse
from aegisai.services.redis_util import get_redis_client

_IDEM_REDIS_PREFIX = "aegisai:idem:"

_jobs: dict[str, JobStatusResponse] = {}
_requests: dict[str, JobRequest] = {}
_attempts: dict[str, int] = {}
_dead_letter: set[str] = set()
_idempotency: dict[str, str] = {}
_idempotency_hash: dict[str, str] = {}
_lock = asyncio.Lock()
_loaded = False


def _state_path() -> Path:
    p = Path(get_settings().chroma_persist_dir.parent) / "job_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _dump() -> None:
    out = {
        "jobs": {k: v.model_dump(mode="json") for k, v in _jobs.items()},
        "requests": {k: v.model_dump(mode="json") for k, v in _requests.items()},
        "attempts": dict(_attempts),
        "dead_letter": sorted(_dead_letter),
        "idempotency": dict(_idempotency),
        "idempotency_hash": dict(_idempotency_hash),
    }
    _state_path().write_text(json.dumps(out, default=str), encoding="utf-8")


def _load() -> None:
    global _loaded
    if _loaded:
        return
    p = _state_path()
    if not p.exists():
        _loaded = True
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        jobs = data.get("jobs") or {}
        reqs = data.get("requests") or {}
        attempts = data.get("attempts") or {}
        dead = data.get("dead_letter") or []
        idem = data.get("idempotency") or {}
        idem_h = data.get("idempotency_hash") or {}
        for k, v in jobs.items():
            _jobs[str(k)] = JobStatusResponse.model_validate(v)
        for k, v in reqs.items():
            _requests[str(k)] = JobRequest.model_validate(v)
        for k, v in attempts.items():
            _attempts[str(k)] = int(v)
        for x in dead:
            _dead_letter.add(str(x))
        for k, v in idem.items():
            _idempotency[str(k)] = str(v)
        for k, v in idem_h.items():
            _idempotency_hash[str(k)] = str(v)
    except Exception:
        # Fail-open for corrupted local state files.
        pass
    _loaded = True


def utcnow() -> datetime:
    return datetime.now(UTC)


async def set_job(job_id: str, payload: JobStatusResponse) -> None:
    async with _lock:
        _load()
        _jobs[job_id] = payload
        _dump()


async def set_job_with_request(
    job_id: str,
    payload: JobStatusResponse,
    body: JobRequest,
) -> None:
    async with _lock:
        _load()
        _jobs[job_id] = payload
        _requests[job_id] = body
        _dump()


async def patch_job(job_id: str, **updates: Any) -> None:
    async with _lock:
        _load()
        cur = _jobs[job_id]
        _jobs[job_id] = cur.model_copy(update=updates)
        _dump()


async def get_job(job_id: str) -> JobStatusResponse | None:
    async with _lock:
        _load()
        return _jobs.get(job_id)


async def get_job_request(job_id: str) -> JobRequest | None:
    async with _lock:
        _load()
        return _requests.get(job_id)


async def list_recoverable_jobs() -> list[str]:
    async with _lock:
        _load()
        out: list[str] = []
        for jid, job in _jobs.items():
            if job.status in (JobStatus.queued, JobStatus.running) and jid in _requests:
                out.append(jid)
        return out


async def increment_attempt(job_id: str) -> int:
    async with _lock:
        _load()
        n = int(_attempts.get(job_id, 0)) + 1
        _attempts[job_id] = n
        _dump()
        return n


async def mark_dead_letter(job_id: str) -> None:
    async with _lock:
        _load()
        _dead_letter.add(job_id)
        _dump()


async def is_dead_letter(job_id: str) -> bool:
    async with _lock:
        _load()
        return job_id in _dead_letter


async def idempotency_get(key: str) -> str | None:
    r = get_redis_client()
    if r is not None:
        v = await r.get(_IDEM_REDIS_PREFIX + key)
        return str(v) if v is not None else None
    async with _lock:
        _load()
        return _idempotency.get(key)


async def idempotency_get_request_hash(key: str) -> str | None:
    r = get_redis_client()
    if r is not None:
        v = await r.get(_IDEM_REDIS_PREFIX + key + ":hash")
        return str(v) if v is not None else None
    async with _lock:
        _load()
        return _idempotency_hash.get(key)


async def idempotency_put_if_absent(
    key: str,
    job_id: str,
    request_hash: str | None = None,
) -> str | None:
    """Returns existing job_id if key is already mapped; else stores key→job_id and returns None."""
    r = get_redis_client()
    if r is not None:
        rk = _IDEM_REDIS_PREFIX + key
        ttl = get_settings().idempotency_ttl_seconds
        ok = await r.set(rk, job_id, nx=True, ex=ttl)
        if ok:
            if request_hash:
                await r.set(_IDEM_REDIS_PREFIX + key + ":hash", request_hash, ex=ttl)
            return None
        existing = await r.get(rk)
        return str(existing) if existing is not None else None
    async with _lock:
        _load()
        cur = _idempotency.get(key)
        if cur is not None:
            return cur
        _idempotency[key] = job_id
        if request_hash:
            _idempotency_hash[key] = request_hash
        _dump()
        return None


async def idempotency_delete(key: str) -> None:
    r = get_redis_client()
    if r is not None:
        await r.delete(_IDEM_REDIS_PREFIX + key)
        await r.delete(_IDEM_REDIS_PREFIX + key + ":hash")
        return
    async with _lock:
        _load()
        _idempotency.pop(key, None)
        _idempotency_hash.pop(key, None)
        _dump()


async def reset_test_state() -> None:
    """Clear in-memory jobs and idempotency (pytest)."""
    global _loaded
    async with _lock:
        _jobs.clear()
        _requests.clear()
        _attempts.clear()
        _dead_letter.clear()
        _idempotency.clear()
        _idempotency_hash.clear()
        _loaded = False
        p = _state_path()
        if p.exists():
            p.unlink()

