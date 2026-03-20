"""Optional per-IP rate limit for /v1 (rolling 1-minute window, in-process or Redis)."""

from __future__ import annotations

import asyncio
import secrets
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from aegisai.config import get_settings
from aegisai.services import metrics
from aegisai.services.redis_util import get_redis_client

_LOCK = asyncio.Lock()
_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_WINDOW_S = 60.0
_RL_REDIS_PREFIX = "aegisai:rl:"


async def _redis_sliding_window_allow(r, client_key: str, limit: int) -> bool:
    """Return True if request may proceed; False if rate limited."""
    rkey = _RL_REDIS_PREFIX + client_key
    now = time.time()
    member = f"{now:.6f}:{secrets.token_hex(6)}"
    await r.zremrangebyscore(rkey, "-inf", now - _WINDOW_S)
    n = await r.zcard(rkey)
    if n >= limit:
        return False
    await r.zadd(rkey, {member: now})
    await r.expire(rkey, int(_WINDOW_S) + 5)
    return True


async def reset_for_tests() -> None:
    async with _LOCK:
        _WINDOWS.clear()


def _client_key(request: Request) -> str:
    if request.client and request.client.host:
        return str(request.client.host)
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """When AEGISAI_RATE_LIMIT_PER_MINUTE is set, cap /v1/* per client IP."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        limit = settings.rate_limit_per_minute
        path = request.url.path
        if limit is None or not path.startswith("/v1/"):
            return await call_next(request)

        key = _client_key(request)
        r = get_redis_client()
        if r is not None:
            allowed = await _redis_sliding_window_allow(r, key, limit)
            if not allowed:
                await metrics.record_rate_limited()
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
            return await call_next(request)

        now = time.monotonic()
        async with _LOCK:
            dq = _WINDOWS[key]
            while dq and now - dq[0] > _WINDOW_S:
                dq.popleft()
            if len(dq) >= limit:
                await metrics.record_rate_limited()
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
            dq.append(now)

        return await call_next(request)
