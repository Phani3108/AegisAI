from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from aegisai.services.request_context import set_request_id


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Propagate X-Request-ID (or generate) for correlating logs and client retries."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = rid
        set_request_id(rid)
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        set_request_id(None)
        return response
