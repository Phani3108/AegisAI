from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from aegisai.config import Settings
from aegisai.ollama.client import OllamaClient
from aegisai.pipelines.image import run_image_pipeline
from aegisai.schemas.jobs import InputType, JobInput, JobRequest

# 1x1 transparent PNG
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.mark.asyncio
async def test_run_image_pipeline_two_step_ollama(tmp_path: Path) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(_TINY_PNG)
    uri = img.resolve().as_uri()

    n = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/chat":
            n["count"] += 1
            if n["count"] == 1:
                return httpx.Response(
                    200,
                    json={
                        "message": {"content": "A tiny square image."},
                        "prompt_eval_count": 10,
                        "eval_count": 20,
                    },
                )
            return httpx.Response(
                200,
                json={
                    "message": {"content": "It is minimal."},
                    "prompt_eval_count": 5,
                    "eval_count": 15,
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    settings = Settings(
        ollama_base_url="http://ollama.test",
        vision_model="llava",
        llm_model="llama3.2",
    )
    body = JobRequest(
        inputs=[
            JobInput(type=InputType.image_ref, uri=uri),
            JobInput(type=InputType.text, text="What is it?"),
        ],
    )

    async with httpx.AsyncClient(transport=transport) as client:
        ollama = OllamaClient(settings.ollama_base_url, client, timeout_s=30.0)
        out = await run_image_pipeline(body, settings, ollama)

    assert n["count"] == 2
    assert "minimal" in out.answer.lower()
    assert out.prompt_tokens_hint == 15
    assert out.eval_tokens_hint == 35
