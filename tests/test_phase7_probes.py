"""Phase 7: /live and /ready (Kubernetes-style) + readiness details."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from aegisai.main import app


def test_live() -> None:
    with TestClient(app) as client:
        r = client.get("/live")
        assert r.status_code == 200
        assert r.json() == {"status": "alive"}


def test_ready_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_tags(self):
        return {"models": [{"name": "llama"}]}

    monkeypatch.setattr("aegisai.services.readiness.OllamaClient.tags", fake_tags)
    with TestClient(app) as client:
        r = client.get("/ready")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"
        assert body["ollama"] == "ok"
        assert body["chroma"] == "ok"
        assert body["models"] == ["llama"]


def test_ready_503_when_ollama_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(self):
        raise RuntimeError("ollama down")

    monkeypatch.setattr("aegisai.services.readiness.OllamaClient.tags", boom)
    with TestClient(app) as client:
        r = client.get("/ready")
        assert r.status_code == 503
        assert "not ready" in r.json().get("detail", "")


def test_v1_ready_same_payload_with_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_tags(self):
        return {"models": [{"name": "x"}]}

    monkeypatch.setenv("AEGISAI_API_KEY", "gate-key")
    monkeypatch.setattr("aegisai.services.readiness.OllamaClient.tags", fake_tags)

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r_bad = await ac.get("/v1/ready")
            assert r_bad.status_code == 401
            r_ok = await ac.get("/v1/ready", headers={"Authorization": "Bearer gate-key"})
            assert r_ok.status_code == 200
            assert r_ok.json()["status"] == "ready"

    import asyncio

    asyncio.run(run())


def test_probes_exempt_when_api_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_tags(self):
        return {"models": []}

    monkeypatch.setenv("AEGISAI_API_KEY", "k")
    monkeypatch.setattr("aegisai.services.readiness.OllamaClient.tags", fake_tags)
    with TestClient(app) as client:
        assert client.get("/live").status_code == 200
        assert client.get("/ready").status_code == 200
