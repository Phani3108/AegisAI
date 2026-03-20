from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegisai.main import app

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def tiny_image(tmp_path: Path) -> Path:
    p = tmp_path / "dlp.png"
    p.write_bytes(_TINY_PNG)
    return p


def test_dlp_blocks_hybrid_when_enabled(
    tiny_image: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AEGISAI_DLP_ENABLED", "true")
    monkeypatch.setenv("AEGISAI_DLP_BLOCK_HYBRID", "true")
    uri = tiny_image.resolve().as_uri()
    payload = {
        "inputs": [
            {"type": "image_ref", "uri": uri},
            {"type": "text", "text": "SSN 123-45-6789"},
        ],
        "sensitivity_label": "internal",
        "mode": "hybrid",
    }
    with TestClient(app) as client:
        r = client.post("/v1/jobs", json=payload)
        assert r.status_code == 400
        assert "dlp" in r.json().get("detail", "").lower()


def test_dlp_allows_local_only_with_same_text(
    tiny_image: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AEGISAI_DLP_ENABLED", "true")

    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        _ = model, messages, stream
        return {"message": {"content": "x"}, "prompt_eval_count": 1, "eval_count": 1}

    monkeypatch.setattr("aegisai.ollama.client.OllamaClient.chat", fake_chat)

    uri = tiny_image.resolve().as_uri()
    payload = {
        "inputs": [
            {"type": "image_ref", "uri": uri},
            {"type": "text", "text": "SSN 123-45-6789"},
        ],
        "sensitivity_label": "internal",
        "mode": "local_only",
    }
    with TestClient(app) as client:
        r = client.post("/v1/jobs", json=payload)
        assert r.status_code == 200
