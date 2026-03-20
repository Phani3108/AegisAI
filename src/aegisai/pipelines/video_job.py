from __future__ import annotations

import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from aegisai.config import Settings
from aegisai.ollama.client import OllamaClient
from aegisai.pipelines.io_util import file_to_image_base64, resolve_file_uri
from aegisai.pipelines.video import extract_keyframes
from aegisai.pipelines.vision_steps import (
    frame_prompt,
    llm_answer_from_evidence,
    merge_token_hints,
    vision_single_shot,
)
from aegisai.schemas.jobs import InputType, JobInput, JobRequest
from aegisai.schemas.video import SamplingPolicy


@dataclass
class VideoPipelineResult:
    answer: str
    frame_descriptions: list[str]
    ingest_ms: int
    vision_ms: int
    llm_ms: int
    frame_count: int
    vision_model: str
    llm_model: str
    prompt_tokens_hint: int | None
    eval_tokens_hint: int | None


def _pick_user_question(inputs: list[JobInput]) -> str:
    for item in inputs:
        if item.type == InputType.text and item.text:
            return item.text.strip()
    return "Summarize what happens in this video and note any important on-screen text."


def _first_video_uri(inputs: list[JobInput]) -> str:
    for item in inputs:
        if item.type == InputType.video_ref and item.uri:
            return item.uri
    raise ValueError("no video_ref with uri in inputs")


async def run_video_pipeline(
    request: JobRequest,
    settings: Settings,
    ollama: OllamaClient,
    *,
    sampling: SamplingPolicy | None = None,
) -> VideoPipelineResult:
    policy = sampling or SamplingPolicy()
    t0 = time.perf_counter()
    uri = _first_video_uri(request.inputs)
    video_path = resolve_file_uri(uri, settings)
    user_question = _pick_user_question(request.inputs)

    tmp = Path(tempfile.mkdtemp(prefix="aegisai_vid_"))
    descriptions: list[str] = []
    vision_bodies: list[dict] = []
    vision_ms = 0
    try:
        frames = extract_keyframes(video_path, policy, tmp)
        ingest_ms = int((time.perf_counter() - t0) * 1000)
        if not frames:
            raise RuntimeError("no frames extracted; check ffmpeg / video file")
        t_vis = time.perf_counter()
        total = len(frames)
        for i, frame_path in enumerate(frames, start=1):
            b64 = file_to_image_base64(frame_path)
            desc, body = await vision_single_shot(
                ollama,
                settings.vision_model,
                b64,
                frame_prompt(i, total),
            )
            descriptions.append(f"[Frame {i}/{total}] {desc}")
            vision_bodies.append(body)
        vision_ms = int((time.perf_counter() - t_vis) * 1000)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    evidence = "\n\n".join(descriptions)
    t_llm = time.perf_counter()
    answer, llm_body = await llm_answer_from_evidence(
        ollama,
        settings.llm_model,
        evidence_title="video frame descriptions (sampled)",
        evidence_text=evidence,
        user_question=user_question,
        output_schema=request.output_schema,
    )
    llm_ms = int((time.perf_counter() - t_llm) * 1000)

    hint_bodies = [*vision_bodies, llm_body]
    prompt_hint, eval_hint = merge_token_hints(*hint_bodies)

    return VideoPipelineResult(
        answer=answer,
        frame_descriptions=descriptions,
        ingest_ms=ingest_ms,
        vision_ms=vision_ms,
        llm_ms=llm_ms,
        frame_count=total,
        vision_model=settings.vision_model,
        llm_model=settings.llm_model,
        prompt_tokens_hint=prompt_hint,
        eval_tokens_hint=eval_hint,
    )
