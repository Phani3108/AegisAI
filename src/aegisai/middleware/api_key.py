from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from aegisai.config import get_settings


def _exempt_path(path: str) -> bool:
    if path in ("/health", "/version", "/metrics", "/openapi.json", "/favicon.ico"):
        return True
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    return False


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Optional shared-secret gate for /v1 when AEGISAI_API_KEY is set."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        expected = (settings.api_key or "").strip()
        path = request.url.path
        if not expected or _exempt_path(path) or not path.startswith("/v1/"):
            return await call_next(request)

        auth = request.headers.get("authorization") or ""
        token: str | None = None
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        if not token:
            token = (request.headers.get("x-api-key") or "").strip() or None
        if token != expected:
            return JSONResponse(
                status_code=401,
                content={"detail": "unauthorized"},
            )
        return await call_next(request)
