from __future__ import annotations

import asyncio


class JobConcurrencyLimiter:
    """Tracks in-flight async jobs; used to cap parallel pipeline work (T1-style guard)."""

    def __init__(self, max_concurrent: int) -> None:
        self._max = max_concurrent
        self._n = 0
        self._lock = asyncio.Lock()

    @property
    def in_flight(self) -> int:
        return self._n

    async def acquire(self) -> bool:
        async with self._lock:
            if self._n >= self._max:
                return False
            self._n += 1
            return True

    async def release(self) -> None:
        async with self._lock:
            if self._n > 0:
                self._n -= 1


_limiter: JobConcurrencyLimiter | None = None


def configure_limiter(max_concurrent: int) -> None:
    global _limiter
    _limiter = JobConcurrencyLimiter(max_concurrent)


def get_limiter() -> JobConcurrencyLimiter:
    if _limiter is None:
        configure_limiter(8)
    assert _limiter is not None
    return _limiter


def reset_limiter_for_tests(max_concurrent: int = 32) -> None:
    configure_limiter(max_concurrent)
