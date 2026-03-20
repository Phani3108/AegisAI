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
    p = tmp_path / "a.png"
    p.write_bytes(_TINY_PNG)
    return p


def test_audit_not_found() -> None:
    with TestClient(app) as client:
        r = client.get("/v1/jobs/00000000-0000-0000-0000-000000000001/audit")
        assert r.status_code == 404


def test_audit_json_and_ndjson(tiny_image: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        _ = model, messages, stream
        return {"message": {"content": "x"}, "prompt_eval_count": 1, "eval_count": 1}

    monkeypatch.setattr("aegisai.ollama.client.OllamaClient.chat", fake_chat)

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
        j = client.get(f"/v1/jobs/{jid}/audit")
        assert j.status_code == 200
        data = j.json()
        assert isinstance(data, list)
        assert data and data[0].get("stage") == "policy"
        n = client.get(f"/v1/jobs/{jid}/audit", params={"format": "ndjson"})
        assert n.status_code == 200
        lines = [ln for ln in n.text.strip().split("\n") if ln.strip()]
        assert len(lines) >= 1
