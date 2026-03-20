from __future__ import annotations

import base64
import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from aegisai.main import app


def _token(secret: str, roles: list[str]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": "u1", "roles": roles}
    h = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).rstrip(b"=").decode("ascii")
    p = (
        base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
        .rstrip(b"=")
        .decode("ascii")
    )
    signed = f"{h}.{p}".encode()
    sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).digest()
    s = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{h}.{p}.{s}"


def test_jwt_mode_auth_for_v1(monkeypatch) -> None:
    monkeypatch.setenv("AEGISAI_AUTH_MODE", "jwt")
    monkeypatch.setenv("AEGISAI_JWT_SECRET", "phase16-secret")
    with TestClient(app) as client:
        r0 = client.get("/v1/policy")
        assert r0.status_code == 401
        tok = _token("phase16-secret", ["operator"])
        r1 = client.get("/v1/policy", headers={"Authorization": f"Bearer {tok}"})
        assert r1.status_code == 200


def test_ops_endpoints_can_be_protected(monkeypatch) -> None:
    monkeypatch.setenv("AEGISAI_AUTH_MODE", "jwt")
    monkeypatch.setenv("AEGISAI_JWT_SECRET", "phase16-secret")
    monkeypatch.setenv("AEGISAI_PROTECT_OPS_ENDPOINTS", "true")
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 401
        tok = _token("phase16-secret", ["operator"])
        assert client.get("/ready", headers={"Authorization": f"Bearer {tok}"}).status_code in (
            200,
            503,
        )
