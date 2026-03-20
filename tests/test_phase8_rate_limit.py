"""Phase 8: optional /v1 rate limiting (per client IP, rolling minute)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from aegisai.main import app


def test_rate_limit_allows_under_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGISAI_RATE_LIMIT_PER_MINUTE", "10")
    with TestClient(app) as client:
        r = client.get("/v1/policy")
        assert r.status_code == 200


def test_rate_limit_429_and_metric(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGISAI_RATE_LIMIT_PER_MINUTE", "2")
    with TestClient(app) as client:
        assert client.get("/v1/policy").status_code == 200
        assert client.get("/v1/policy").status_code == 200
        r3 = client.get("/v1/policy")
        assert r3.status_code == 429
        assert r3.json().get("detail") == "rate limit exceeded"
        assert r3.headers.get("Retry-After") == "60"

        # Counter via /metrics (not under /v1, so not subject to the same limit bucket).
        prom = client.get("/metrics").text
        assert "aegisai_http_429_rate_limited_total 1" in prom


def test_rate_limit_not_applied_outside_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGISAI_RATE_LIMIT_PER_MINUTE", "1")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
