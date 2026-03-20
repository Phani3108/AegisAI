"""Optional per-IP rate limit for /v1 (rolling 1-minute window, in-process)."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from aegisai.config import get_settings
from aegisai.services import metrics

_LOCK = asyncio.Lock()
_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_WINDOW_S = 60.0


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

        now = time.monotonic()
        key = _client_key(request)
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
