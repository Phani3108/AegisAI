from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from aegisai.config import Settings
from aegisai.inference.factory import create_inference_backend
from aegisai.main import app
from aegisai.ollama.client import OllamaClient
from aegisai.schemas.jobs import (
    InputType,
    JobEvent,
    JobInput,
    JobRequest,
    JobStatus,
    JobStatusResponse,
)
from aegisai.services import job_cancel, job_store
from aegisai.services.job_runner import execute_job

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def tiny_image(tmp_path: Path) -> Path:
    p = tmp_path / "c4.png"
    p.write_bytes(_TINY_PNG)
    return p


@pytest.mark.asyncio
async def test_execute_job_respects_pre_cancel_flag() -> None:
    from aegisai.services import metrics

    jid = str(uuid.uuid4())
    now = datetime.now(UTC)
    await job_cancel.request_cancel(jid)
    await job_store.set_job(
        jid,
        JobStatusResponse(
            job_id=jid,
            status=JobStatus.queued,
            created_at=now,
            updated_at=now,
            route="local_only",
            events=[
                JobEvent(
                    ts=now,
                    stage="policy",
                    message="p",
                    route="local_only",
                )
            ],
            result=None,
            error=None,
        ),
    )
    body = JobRequest(
        inputs=[
            JobInput(type=InputType.image_ref, uri="file:///dev/null"),
            JobInput(type=InputType.text, text="?"),
        ],
        sensitivity_label="internal",
        mode="local_only",
    )
    settings = Settings(ollama_base_url="http://noop")
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    async with httpx.AsyncClient(transport=transport) as http:
        inference = create_inference_backend(settings, http)
        await execute_job(jid, body, settings, inference, None)

    final = await job_store.get_job(jid)
    assert final is not None
    assert final.status == JobStatus.cancelled
    assert any("cancelled" in (ev.message or "").lower() for ev in final.events)

    snap = await metrics.snapshot()
    assert snap.get("jobs_cancelled_total", 0) >= 1
    assert snap.get("by_pipeline", {}).get("image", {}).get("cancelled", 0) >= 1


def test_post_cancel_returns_404_for_unknown() -> None:
    with TestClient(app) as client:
        r = client.post("/v1/jobs/00000000-0000-0000-0000-000000000099/cancel")
        assert r.status_code == 404


def test_post_cancel_idempotent_on_terminal(
    tiny_image: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_chat(
        self, model: str, messages: list, *, stream: bool = False, **_kw: object
    ):
        _ = model, messages, stream
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
        jid = r.json()["job_id"]
        r2 = client.post(f"/v1/jobs/{jid}/cancel")
        assert r2.status_code == 200
        d = r2.json()
        assert d.get("cancel_requested") in (True, False)
        r3 = client.post(f"/v1/jobs/{jid}/cancel")
        assert r3.status_code == 200
        assert r3.json().get("cancel_requested") is False


def test_websocket_job_events_done(tiny_image: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(
        self, model: str, messages: list, *, stream: bool = False, **_kw: object
    ):
        _ = model, messages, stream
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
        jid = r.json()["job_id"]
        with client.websocket_connect(f"/v1/ws/jobs/{jid}") as ws:
            msgs: list[dict] = []
            while len(msgs) < 50:
                msgs.append(ws.receive_json())
                if msgs[-1].get("type") == "done":
                    break
        assert any(m.get("type") == "event" for m in msgs)
        assert msgs[-1].get("type") == "done"
