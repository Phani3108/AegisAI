#!/usr/bin/env python3
"""Benchmark v0: wall time + stage ms for one image job (requires running Ollama)."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx

from aegisai.config import get_settings
from aegisai.ollama.client import OllamaClient
from aegisai.pipelines.image import run_image_pipeline
from aegisai.schemas.jobs import InputType, JobInput, JobRequest


async def main() -> None:
    p = argparse.ArgumentParser(description="AegisAI benchmark v0 (image pipeline)")
    p.add_argument("image", type=Path, help="Path to image file")
    p.add_argument(
        "--question",
        default="",
        help="Optional user question (else default summary prompt is used)",
    )
    args = p.parse_args()

    settings = get_settings()
    path = args.image.resolve()
    uri = path.as_uri()
    inputs: list[JobInput] = [JobInput(type=InputType.image_ref, uri=uri)]
    if args.question:
        inputs.append(JobInput(type=InputType.text, text=args.question))

    body = JobRequest(inputs=inputs, sensitivity_label="internal", mode="local_only")

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=settings.ollama_timeout_s) as client:
        ollama = OllamaClient(settings.ollama_base_url, client, timeout_s=settings.ollama_timeout_s)
        out = await run_image_pipeline(body, settings, ollama)
    wall_ms = int((time.perf_counter() - t0) * 1000)

    report = {
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
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
