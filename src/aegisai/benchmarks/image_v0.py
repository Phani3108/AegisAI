"""Image pipeline benchmark (wall clock + stage ms); used by benchmarks/run_v0.py CLI."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

from aegisai.config import Settings, get_settings
from aegisai.ollama.client import OllamaClient
from aegisai.pipelines.image import run_image_pipeline
from aegisai.schemas.jobs import InputType, JobInput, JobRequest


async def run_image_benchmark(
    image: Path,
    *,
    question: str = "",
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Run one image job via `run_image_pipeline` and return a JSON-serializable report dict."""
    settings = settings or get_settings()
    path = image.resolve()
    uri = path.as_uri()
    inputs: list[JobInput] = [JobInput(type=InputType.image_ref, uri=uri)]
    if question:
        inputs.append(JobInput(type=InputType.text, text=question))
    body = JobRequest(inputs=inputs, sensitivity_label="internal", mode="local_only")

    t0 = time.perf_counter()

    async def _run(c: httpx.AsyncClient) -> dict[str, Any]:
        ollama = OllamaClient(settings.ollama_base_url, c, timeout_s=settings.ollama_timeout_s)
        out = await run_image_pipeline(body, settings, ollama)
        wall_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "image": str(path),
            "vision_model": out.vision_model,
            "llm_model": out.llm_model,
            "vision_ms": out.vision_ms,
            "llm_ms": out.llm_ms,
            "wall_ms": wall_ms,
            "prompt_tokens_hint": out.prompt_tokens_hint,
            "eval_tokens_hint": out.eval_tokens_hint,
            "answer_preview": (out.answer[:400] + "…") if len(out.answer) > 400 else out.answer,
        }

    if client is None:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_s) as c:
            return await _run(c)
    return await _run(client)
