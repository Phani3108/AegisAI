from __future__ import annotations

import base64
import hashlib
import hmac
import json

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from aegisai.config import get_settings


def _exempt_path(path: str, *, protect_ops_endpoints: bool) -> bool:
    if path in (
        "/health",
        "/live",
        "/version",
        "/openapi.json",
        "/favicon.ico",
    ):
        return True
    if not protect_ops_endpoints and path in ("/ready", "/metrics"):
        return True
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    return False


def _jwt_authorized(request: Request, secret: str, algorithm: str) -> bool:
    if algorithm.upper() != "HS256":
        return False
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return False
    token = auth[7:].strip()
    if not token:
        return False
    parts = token.split(".")
    if len(parts) != 3:
        return False
    head_b64, payload_b64, sig_b64 = parts
    signed = f"{head_b64}.{payload_b64}".encode()
    expect_sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).digest()
    expect_b64 = base64.urlsafe_b64encode(expect_sig).rstrip(b"=").decode("ascii")
    if not hmac.compare_digest(expect_b64, sig_b64):
        return False
    try:
        pad = "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64 + pad).decode("utf-8"))
    except Exception:
        return False
    roles = claims.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    request.state.user_roles = [str(r) for r in roles]
    request.state.user_sub = str(claims.get("sub") or "")
    return True


def _api_key_authorized(request: Request, expected: str) -> bool:
    auth = request.headers.get("authorization") or ""
    token: str | None = None
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        token = (request.headers.get("x-api-key") or "").strip() or None
    return token == expected


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Optional shared-secret gate for /v1 when AEGISAI_API_KEY is set."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        expected = (settings.api_key or "").strip()
        mode = (settings.auth_mode or "api_key").strip().lower()
        secret = (settings.jwt_secret or "").strip()
        path = request.url.path
        if _exempt_path(path, protect_ops_endpoints=settings.protect_ops_endpoints):
            return await call_next(request)
        needs_auth = path.startswith("/v1/") or (
            settings.protect_ops_endpoints and path in ("/ready", "/metrics")
        )
        if not needs_auth:
            return await call_next(request)
        if mode == "api_key" and not expected:
            return await call_next(request)
        if mode == "jwt" and not secret:
            return await call_next(request)
        if mode == "both" and not expected and not secret:
            return await call_next(request)

        authed = False
        if mode in ("api_key", "both") and expected:
            authed = _api_key_authorized(request, expected)
        if not authed and mode in ("jwt", "both") and secret:
            authed = _jwt_authorized(request, secret, settings.jwt_algorithm)
        if not authed:
            return JSONResponse(
                status_code=401,
                content={"detail": "unauthorized"},
            )
        return await call_next(request)
