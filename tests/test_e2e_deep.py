"""
End-to-end API surface: health → policy → Chroma ingest → rag_collection job → job status.
Uses mocked Ollama (no daemon required).
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegisai.main import app
from aegisai.ollama.client import OllamaClient


@pytest.fixture
def e2e_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("AEGISAI_CHROMA_PERSIST_DIR", str(tmp_path / "chroma_e2e"))

    async def fake_embed(self, model: str, prompt: str) -> list[float]:
        _ = model, prompt
        return [0.125] * 8

    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        _ = model, messages, stream
        return {"message": {"content": "e2e-answer"}, "prompt_eval_count": 2, "eval_count": 3}

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)
    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    with TestClient(app) as client:
        yield client


def test_e2e_health_policy_collections_job_flow(e2e_client: TestClient) -> None:
    c = e2e_client

    h = c.get("/health")
    assert h.status_code == 200
    assert h.json() == {"status": "ok"}

    pol = c.get("/v1/policy")
    assert pol.status_code == 200
    body = pol.json()
    assert "version" in body and "hybrid_allowed_labels" in body

    cols = c.get("/v1/collections")
    assert cols.status_code == 200
    assert "collections" in cols.json()

    cr = c.post("/v1/collections", json={"name": "demo_kb"})
    assert cr.status_code == 200
    assert cr.json().get("name")

    ing = c.post(
        "/v1/collections/demo_kb/documents",
        json={
            "documents": [
                {
                    "id": "doc-a",
                    "text": ("The quick brown fox jumps. " * 30),
                    "metadata": {"source": "e2e"},
                }
            ]
        },
    )
    assert ing.status_code == 200
    assert ing.json().get("chunks_added", 0) >= 1

    jr = c.post(
        "/v1/jobs",
        json={
            "inputs": [{"type": "text", "text": "What animal is mentioned?"}],
            "rag_collection": "demo_kb",
            "sensitivity_label": "internal",
            "mode": "local_only",
        },
    )
    assert jr.status_code == 200
    job_id = jr.json()["job_id"]

    st = c.get(f"/v1/jobs/{job_id}")
    assert st.status_code == 200
    data = st.json()
    assert data["status"] == "succeeded"
    assert "e2e-answer" in (data.get("result") or {}).get("text", "").lower()
    assert data.get("result", {}).get("structured", {}).get("store") == "chroma"
    assert any(e.get("stage") == "policy" for e in data.get("events", []))


def test_e2e_image_job_mocked_ollama(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Image path: two chat calls (vision + LLM) via TestClient."""
    _png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    img = tmp_path / "e2e.png"
    img.write_bytes(_png)
    uri = img.resolve().as_uri()

    n = {"c": 0}

    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        n["c"] += 1
        if n["c"] == 1:
            return {"message": {"content": "a square"}, "prompt_eval_count": 1, "eval_count": 1}
        return {"message": {"content": "it is a shape"}, "prompt_eval_count": 1, "eval_count": 1}

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)
    monkeypatch.setenv("AEGISAI_CHROMA_PERSIST_DIR", str(tmp_path / "ch_img"))

    with TestClient(app) as client:
        r = client.post(
            "/v1/jobs",
            json={
                "inputs": [
                    {"type": "image_ref", "uri": uri},
                    {"type": "text", "text": "Describe briefly."},
                ],
                "mode": "local_only",
            },
        )
        assert r.status_code == 200
        jid = r.json()["job_id"]
        st = client.get(f"/v1/jobs/{jid}").json()
        assert st["status"] == "succeeded"
        assert n["c"] == 2
