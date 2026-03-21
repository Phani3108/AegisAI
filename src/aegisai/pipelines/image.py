from __future__ import annotations

import time
from dataclasses import dataclass

from aegisai.config import Settings
from aegisai.inference.protocol import InferenceBackend
from aegisai.pipelines.io_util import file_to_image_base64, materialize_uri
from aegisai.pipelines.vision_steps import (
    VISION_PROMPT_IMAGE,
    llm_answer_from_evidence,
    merge_token_hints,
    vision_single_shot,
)
from aegisai.schemas.jobs import InputType, JobInput, JobRequest


@dataclass
class ImagePipelineResult:
    answer: str
    vision_description: str
    vision_ms: int
    llm_ms: int
    ingest_ms: int
    vision_model: str
    llm_model: str
    prompt_tokens_hint: int | None
    eval_tokens_hint: int | None


def _pick_user_question(inputs: list[JobInput]) -> str:
    for item in inputs:
        if item.type == InputType.text and item.text:
            return item.text.strip()
    return "Summarize the key information from the image for an enterprise review."


def _first_image_uri(inputs: list[JobInput]) -> str:
    for item in inputs:
        if item.type == InputType.image_ref and item.uri:
            return item.uri
    raise ValueError("no image_ref with uri in inputs")


async def run_image_pipeline(
    request: JobRequest,
    settings: Settings,
    ollama: InferenceBackend,
) -> ImagePipelineResult:
    t_ingest = time.perf_counter()
    uri = _first_image_uri(request.inputs)
    path, temps = await materialize_uri(uri, settings)
    try:
        image_b64 = file_to_image_base64(path)
        user_question = _pick_user_question(request.inputs)
        ingest_ms = int((time.perf_counter() - t_ingest) * 1000)
    finally:
        for p in temps:
            p.unlink(missing_ok=True)

    t0 = time.perf_counter()
    vision_text, vision_body = await vision_single_shot(
        ollama,
        settings.vision_model,
        image_b64,
        VISION_PROMPT_IMAGE,
    )
    vision_ms = int((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    answer, llm_body = await llm_answer_from_evidence(
        ollama,
        settings.llm_model,
        evidence_title="image description",
        evidence_text=vision_text,
        user_question=user_question,
        output_schema=request.output_schema,
    )
    llm_ms = int((time.perf_counter() - t1) * 1000)

    prompt_hint, eval_hint = merge_token_hints(vision_body, llm_body)

    return ImagePipelineResult(
        answer=answer,
        vision_description=vision_text,
        vision_ms=vision_ms,
        llm_ms=llm_ms,
        ingest_ms=ingest_ms,
        vision_model=settings.vision_model,
        llm_model=settings.llm_model,
        prompt_tokens_hint=prompt_hint,
        eval_tokens_hint=eval_hint,
    )
