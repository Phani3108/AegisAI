from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegisai.main import app
from aegisai.ollama.client import OllamaClient


def test_metrics_json_and_prometheus_empty() -> None:
    with TestClient(app) as client:
        j = client.get("/v1/metrics").json()
        assert j["jobs_completed_total"] == 0
        p = client.get("/v1/metrics", params={"format": "prometheus"}).text
        assert "aegisai_jobs_completed_total 0" in p
        p2 = client.get("/metrics").text
        assert "aegisai_jobs_completed_total 0" in p2


def test_metrics_increments_on_job(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        _ = model, messages, stream
        return {"message": {"content": "x"}, "prompt_eval_count": 1, "eval_count": 1}

    monkeypatch.setattr(OllamaClient, "chat", fake_chat)

    img = tmp_path / "m.png"
    img.write_bytes(
        __import__("base64").b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
    )
    uri = img.resolve().as_uri()
    monkeypatch.setenv("AEGISAI_CHROMA_PERSIST_DIR", str(tmp_path / "ch"))

    with TestClient(app) as client:
        client.post(
            "/v1/jobs",
            json={
                "inputs": [{"type": "image_ref", "uri": uri}, {"type": "text", "text": "?"}],
                "mode": "local_only",
            },
        )
        j = client.get("/v1/metrics").json()
        assert j["jobs_completed_total"] == 1
        assert j["by_pipeline"].get("image", {}).get("completed") == 1
