from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aegisai.main import app
from aegisai.ollama.client import OllamaClient


def test_rag_collection_with_document_ref_is_422() -> None:
    with TestClient(app) as client:
        r = client.post(
            "/v1/jobs",
            json={
                "inputs": [
                    {"type": "document_ref", "uri": "file:///tmp/x.txt"},
                    {"type": "text", "text": "q"},
                ],
                "rag_collection": "kb",
                "mode": "local_only",
            },
        )
        assert r.status_code == 422


def test_rag_collection_requires_text_question() -> None:
    with TestClient(app) as client:
        r = client.post(
            "/v1/jobs",
            json={
                "inputs": [{"type": "text", "text": "   "}],
                "rag_collection": "kb",
                "mode": "local_only",
            },
        )
        assert r.status_code == 422


@pytest.fixture
def mock_embed_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_embed(self, model: str, prompt: str) -> list[float]:
        _ = model, prompt
        return [0.25] * 8

    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        _ = model, messages, stream
        return {"message": {"content": "chroma-answer"}, "prompt_eval_count": 1, "eval_count": 2}

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)
    monkeypatch.setattr(OllamaClient, "chat", fake_chat)


def test_chroma_ingest_and_rag_job(
    mock_embed_chat: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("AEGISAI_CHROMA_PERSIST_DIR", str(tmp_path / "chroma_data"))
    with TestClient(app) as client:
        r0 = client.post("/v1/collections", json={"name": "knowledge_base"})
        assert r0.status_code == 200
        r1 = client.post(
            "/v1/collections/knowledge_base/documents",
            json={
                "documents": [
                    {
                        "id": "doc1",
                        "text": ("alpha beta gamma delta. " * 40),
                    }
                ]
            },
        )
        assert r1.status_code == 200
        assert r1.json().get("chunks_added", 0) >= 1

        r2 = client.post(
            "/v1/jobs",
            json={
                "inputs": [{"type": "text", "text": "What is alpha?"}],
                "rag_collection": "knowledge_base",
                "mode": "local_only",
            },
        )
        assert r2.status_code == 200
        job_id = r2.json()["job_id"]
        st = client.get(f"/v1/jobs/{job_id}").json()
        assert st["status"] == "succeeded"
        assert "chroma-answer" in (st.get("result") or {}).get("text", "").lower()
        assert st.get("result", {}).get("structured", {}).get("store") == "chroma"


def test_list_collections(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("AEGISAI_CHROMA_PERSIST_DIR", str(tmp_path / "ch2"))
    with TestClient(app) as client:
        client.post("/v1/collections", json={"name": "alpha"})
        r = client.get("/v1/collections")
        assert r.status_code == 200
        assert "alpha" in r.json().get("collections", [])
