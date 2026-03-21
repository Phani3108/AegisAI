"""P20: remote fetch allowlists + collection document source_uri."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aegisai.config import Settings
from aegisai.connectors.fetch import fetch_https_bytes
from aegisai.main import app
from aegisai.ollama.client import OllamaClient
from aegisai.schemas.collections import DocumentBatch, DocumentItem


@pytest.mark.asyncio
async def test_https_fetch_requires_nonempty_allowlist() -> None:
    s = Settings(
        connector_remote_enabled=True,
        connector_https_hosts_allowlist="",
        connector_max_fetch_bytes=4096,
        connector_fetch_timeout_s=30,
    )
    with pytest.raises(ValueError, match="HOSTS_ALLOWLIST"):
        await fetch_https_bytes("https://example.com/x", s)


@pytest.mark.asyncio
async def test_https_disabled_raises() -> None:
    s = Settings(connector_remote_enabled=False)
    with pytest.raises(ValueError, match="CONNECTOR_REMOTE"):
        await fetch_https_bytes("https://example.com/x", s)


def test_document_item_rejects_both_text_and_uri() -> None:
    with pytest.raises(ValueError):
        DocumentItem(id="a", text="x", source_uri="https://x.com/y")


def test_document_item_rejects_neither() -> None:
    with pytest.raises(ValueError):
        DocumentItem(id="a")


def test_document_batch_accepts_source_uri_only() -> None:
    b = DocumentBatch(documents=[DocumentItem(id="a", source_uri="file:///tmp/x.txt")])
    assert b.documents[0].source_uri


@pytest.fixture
def mock_embed_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_embed(self, model: str, prompt: str) -> list[float]:
        _ = model, prompt
        return [0.25] * 8

    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        _ = model, messages, stream
        return {"message": {"content": "ok"}, "prompt_eval_count": 1, "eval_count": 2}

    monkeypatch.setattr(OllamaClient, "embed", fake_embed)
    monkeypatch.setattr(OllamaClient, "chat", fake_chat)


def test_chroma_ingest_source_uri_file(
    mock_embed_chat: None,
    tmp_path,
) -> None:
    doc = tmp_path / "src.txt"
    doc.write_text("alpha beta gamma " * 20, encoding="utf-8")
    with TestClient(app) as client:
        r0 = client.post("/v1/collections", json={"name": "kb_src"})
        assert r0.status_code == 200
        r1 = client.post(
            "/v1/collections/kb_src/documents",
            json={
                "documents": [
                    {"id": "d1", "source_uri": doc.resolve().as_uri()},
                ]
            },
        )
        assert r1.status_code == 200
        assert r1.json().get("chunks_added", 0) >= 1


def test_rag_collection_with_audio_ref_is_422() -> None:
    with TestClient(app) as client:
        r = client.post(
            "/v1/jobs",
            json={
                "inputs": [
                    {"type": "audio_ref", "uri": "file:///tmp/x.wav"},
                    {"type": "text", "text": "q"},
                ],
                "rag_collection": "kb",
                "mode": "local_only",
            },
        )
        assert r.status_code == 422
