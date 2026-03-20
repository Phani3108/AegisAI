from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegisai.main import app
from aegisai.ollama.client import OllamaClient

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def tiny_image(tmp_path: Path) -> Path:
    p = tmp_path / "ph3.png"
    p.write_bytes(_TINY_PNG)
    return p


def test_v1_query_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(
        self,
        model: str,
        messages: list,
        *,
        stream: bool = False,
        response_format: str | None = None,
        **_kw: object,
    ):
        _ = stream, response_format
        assert model == "llama3.2"
        assert messages
        return {"model": model, "message": {"content": "sync-ok"}}

    monkeypatch.setattr("aegisai.ollama.client.OllamaClient.chat", fake_chat)

    with TestClient(app) as client:
        r = client.post(
            "/v1/query",
            json={
                "model": "llama3.2",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        assert r.status_code == 200
        assert r.json()["message"]["content"] == "sync-ok"


def test_job_events_sse_done(tiny_image: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(
        self,
        model: str,
        messages: list,
        *,
        stream: bool = False,
        response_format: str | None = None,
        **_kw: object,
    ):
        _ = model, stream, response_format
        return {"message": {"content": "x"}, "prompt_eval_count": 1, "eval_count": 1}

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    uri = tiny_image.resolve().as_uri()
    payload = {
        "inputs": [{"type": "image_ref", "uri": uri}, {"type": "text", "text": "?"}],
        "sensitivity_label": "internal",
        "mode": "local_only",
    }
    with TestClient(app) as client:
        r = client.post("/v1/jobs", json=payload)
        assert r.status_code == 200
        jid = r.json()["job_id"]
        with client.stream("GET", f"/v1/jobs/{jid}/events") as sr:
            assert sr.status_code == 200
            raw = sr.read().decode()
        assert "data:" in raw
        assert "[DONE]" in raw


def test_output_schema_json_parsed(
    tiny_image: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    n = {"calls": 0}

    async def fake_chat(
        self,
        model: str,
        messages: list,
        *,
        stream: bool = False,
        response_format: str | None = None,
        **_kw: object,
    ):
        n["calls"] += 1
        if n["calls"] == 1:
            return {"message": {"content": "vision"}, "prompt_eval_count": 1, "eval_count": 1}
        assert response_format == "json"
        return {
            "message": {"content": '{"summary":"doc"}'},
            "prompt_eval_count": 1,
            "eval_count": 1,
        }

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    uri = tiny_image.resolve().as_uri()
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}}
    payload = {
        "inputs": [{"type": "image_ref", "uri": uri}, {"type": "text", "text": "What?"}],
        "sensitivity_label": "internal",
        "mode": "local_only",
        "output_schema": schema,
    }
    with TestClient(app) as client:
        r = client.post("/v1/jobs", json=payload)
        assert r.status_code == 200
        jid = r.json()["job_id"]
        job = client.get(f"/v1/jobs/{jid}").json()
        assert job["status"] == "succeeded"
        st = job.get("result", {}).get("structured") or {}
        assert st.get("json_mode") is True
        assert st.get("parsed") == {"summary": "doc"}
