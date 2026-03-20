from __future__ import annotations

from starlette.websockets import WebSocket


def websocket_shared_secret_authorized(websocket: WebSocket, expected: str | None) -> bool:
    """Match HTTP API key rules: Bearer, X-API-Key header, or query ``api_key``."""
    exp = (expected or "").strip()
    if not exp:
        return True
    auth = websocket.headers.get("authorization") or ""
    token: str | None = None
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        token = (websocket.headers.get("x-api-key") or "").strip() or None
    if not token:
        token = (websocket.query_params.get("api_key") or "").strip() or None
    return token == exp
