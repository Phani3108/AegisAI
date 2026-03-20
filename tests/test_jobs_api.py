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
    p = tmp_path / "x.png"
    p.write_bytes(_TINY_PNG)
    return p


def test_create_job_background_succeeds(
    tiny_image: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"message": {"content": "description"}, "prompt_eval_count": 1, "eval_count": 2}
        return {"message": {"content": "answer text"}, "prompt_eval_count": 3, "eval_count": 4}

    monkeypatch.setattr("aegisai.ollama.client.OllamaClient.chat", fake_chat)

    uri = tiny_image.resolve().as_uri()
    payload = {
        "inputs": [
            {"type": "image_ref", "uri": uri},
            {"type": "text", "text": "What?"},
        ],
        "sensitivity_label": "internal",
        "mode": "local_only",
    }

    with TestClient(app) as client:
        r = client.post("/v1/jobs", json=payload)
        assert r.status_code == 200
        job_id = r.json()["job_id"]
        r2 = client.get(f"/v1/jobs/{job_id}")
        assert r2.status_code == 200
        data = r2.json()
        assert data["status"] in ("queued", "running", "succeeded")
        # BackgroundTasks in TestClient complete before handler returns in Starlette 0.37+
        assert data["status"] == "succeeded"
        assert data.get("result", {}).get("text") == "answer text"


def test_media_conflict_marks_job_failed(tiny_image: Path, tmp_path: Path) -> None:
    vid = tmp_path / "a.mp4"
    vid.write_bytes(b"x")
    payload = {
        "inputs": [
            {"type": "image_ref", "uri": tiny_image.resolve().as_uri()},
            {"type": "video_ref", "uri": vid.resolve().as_uri()},
        ],
        "sensitivity_label": "internal",
        "mode": "local_only",
    }
    with TestClient(app) as client:
        r = client.post("/v1/jobs", json=payload)
        assert r.status_code == 200
        job_id = r.json()["job_id"]
        r2 = client.get(f"/v1/jobs/{job_id}")
        assert r2.json()["status"] == "failed"
        assert "only one" in (r2.json().get("error") or "").lower()


def test_hybrid_confidential_rejected() -> None:
    with TestClient(app) as client:
        r = client.post(
            "/v1/jobs",
            json={
                "inputs": [{"type": "image_ref", "uri": "file:///tmp/x"}],
                "sensitivity_label": "regulated",
                "mode": "hybrid",
            },
        )
        assert r.status_code == 400
