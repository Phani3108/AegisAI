from __future__ import annotations

import asyncio
import base64
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from aegisai.main import app
from aegisai.services.job_concurrency import reset_limiter_for_tests
from aegisai.services.job_runner import execute_job as real_execute_job

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def tiny_image(tmp_path: Path) -> Path:
    p = tmp_path / "p.png"
    p.write_bytes(_TINY_PNG)
    return p


def _job_payload(uri: str) -> dict:
    return {
        "inputs": [
            {"type": "image_ref", "uri": uri},
            {"type": "text", "text": "?"},
        ],
        "sensitivity_label": "internal",
        "mode": "local_only",
    }


def test_api_key_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGISAI_API_KEY", "k8s-demo-secret")
    transport = ASGITransport(app=app)
    async def run() -> None:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r0 = await ac.get("/health")
            assert r0.status_code == 200
            r1 = await ac.get("/v1/policy")
            assert r1.status_code == 401
            r2 = await ac.get(
                "/v1/policy",
                headers={"Authorization": "Bearer k8s-demo-secret"},
            )
            assert r2.status_code == 200
            r3 = await ac.get(
                "/v1/policy",
                headers={"X-API-Key": "k8s-demo-secret"},
            )
            assert r3.status_code == 200

    asyncio.run(run())


def test_idempotency_returns_same_job(tiny_image: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"message": {"content": "d"}, "prompt_eval_count": 1, "eval_count": 2}
        return {"message": {"content": "a"}, "prompt_eval_count": 3, "eval_count": 4}

    monkeypatch.setattr("aegisai.ollama.client.OllamaClient.chat", fake_chat)

    uri = tiny_image.resolve().as_uri()
    payload = _job_payload(uri)
    transport = ASGITransport(app=app)

    async def run() -> None:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            h = {"Idempotency-Key": "idem-1"}
            r1 = await ac.post("/v1/jobs", json=payload, headers=h)
            assert r1.status_code == 200
            j1 = r1.json()["job_id"]
            r2 = await ac.post("/v1/jobs", json=payload, headers=h)
            assert r2.status_code == 200
            assert r2.json()["job_id"] == j1

    asyncio.run(run())
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_concurrent_job_cap_429(tiny_image: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_limiter_for_tests(1)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def stall(*args, **kwargs):
        entered.set()
        await release.wait()
        return await real_execute_job(*args, **kwargs)

    monkeypatch.setattr("aegisai.api.routes.v1_jobs.execute_job", stall)

    uri = tiny_image.resolve().as_uri()
    payload = _job_payload(uri)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        t1 = asyncio.create_task(ac.post("/v1/jobs", json=payload))
        await asyncio.wait_for(entered.wait(), timeout=3.0)
        r2 = await ac.post("/v1/jobs", json=payload)
        assert r2.status_code == 429
        release.set()
        r1 = await asyncio.wait_for(t1, timeout=5.0)
        assert r1.status_code == 200
