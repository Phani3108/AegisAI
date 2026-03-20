from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from aegisai.config import Settings
from aegisai.ollama.client import OllamaClient
from aegisai.pipelines.video_job import run_video_pipeline
from aegisai.schemas.jobs import InputType, JobInput, JobRequest
from aegisai.schemas.video import SamplingPolicy

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.mark.asyncio
async def test_run_video_pipeline_monkeypatched_frames(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"not-a-real-video")
    uri = vid.resolve().as_uri()

    def fake_extract(video_path: Path, policy: SamplingPolicy, out_dir: Path) -> list[Path]:
        _ = video_path, policy
        a = out_dir / "a.png"
        b = out_dir / "b.png"
        a.write_bytes(_TINY_PNG)
        b.write_bytes(_TINY_PNG)
        return [a, b]

    monkeypatch.setattr("aegisai.pipelines.video_job.extract_keyframes", fake_extract)

    n = {"calls": 0}

    async def fake_chat(self, model: str, messages: list, *, stream: bool = False):
        n["calls"] += 1
        if n["calls"] <= 2:
            return {
                "message": {"content": f"frame-{n['calls']}"},
                "prompt_eval_count": 1,
                "eval_count": 2,
            }
        return {"message": {"content": "video summary"}, "prompt_eval_count": 3, "eval_count": 4}

    monkeypatch.setattr("aegisai.ollama.client.OllamaClient.chat", fake_chat)

    settings = Settings(ollama_base_url="http://noop", vision_model="lv", llm_model="lm")
    body = JobRequest(
        inputs=[
            JobInput(type=InputType.video_ref, uri=uri),
            JobInput(type=InputType.text, text="What happens?"),
        ],
    )
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    async with httpx.AsyncClient(transport=transport) as client:
        ollama = OllamaClient(settings.ollama_base_url, client, timeout_s=5.0)
        out = await run_video_pipeline(body, settings, ollama)

    assert n["calls"] == 3
    assert out.frame_count == 2
    assert "summary" in out.answer.lower()
    assert out.vision_ms >= 0
