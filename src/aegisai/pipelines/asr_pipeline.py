"""Audio / video-audio transcription pipeline with optional LLM follow-up (P21)."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from aegisai.config import Settings
from aegisai.inference.protocol import InferenceBackend
from aegisai.pipelines.asr_media import media_to_wav_mono16k, wav_duration_seconds
from aegisai.pipelines.io_util import materialize_uri
from aegisai.pipelines.vision_steps import llm_answer_from_evidence, merge_token_hints
from aegisai.schemas.jobs import InputType, JobInput, JobRequest


@dataclass
class AsrPipelineResult:
    answer: str
    transcript: str
    segments: list[dict[str, Any]]
    ingest_ms: int
    asr_ms: int
    llm_ms: int
    segment_count: int
    llm_model: str | None
    prompt_tokens_hint: int | None
    eval_tokens_hint: int | None


def _pick_user_question(inputs: list[JobInput]) -> str:
    for item in inputs:
        if item.type == InputType.text and item.text:
            return item.text.strip()
    return ""


def _first_media_uri(inputs: list[JobInput], kind: Literal["audio", "video"]) -> str:
    want = InputType.audio_ref if kind == "audio" else InputType.video_ref
    for item in inputs:
        if item.type == want and item.uri:
            return item.uri
    raise ValueError(f"no {want.value} with uri in inputs")


def sanitize_segments_payload(segments: list[dict[str, Any]], *, max_n: int = 50) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    for s in segments[:max_n]:
        out.append(
            {
                "start": float(s.get("start", 0.0)),
                "end": float(s.get("end", 0.0)),
                "text": str(s.get("text", ""))[:500],
            }
        )
    return {"segments": out}


async def transcribe_wav_bytes(
    wav: bytes,
    settings: Settings,
) -> tuple[str, list[dict[str, Any]], int]:
    t0 = time.perf_counter()
    if settings.asr_stub:
        dur = wav_duration_seconds(wav)
        end = max(dur, 0.01)
        text = settings.asr_stub_text
        segments: list[dict[str, Any]] = [{"start": 0.0, "end": float(end), "text": text}]
        return text, segments, int((time.perf_counter() - t0) * 1000)
    url = (settings.asr_http_url or "").strip()
    if not url:
        raise RuntimeError("ASR: set AEGISAI_ASR_STUB=true or AEGISAI_ASR_HTTP_URL")
    timeout = httpx.Timeout(settings.asr_http_timeout_s)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            url,
            files={"file": ("audio.wav", wav, "audio/wav")},
        )
        r.raise_for_status()
        try:
            data = r.json()
        except Exception as e:
            raise RuntimeError("ASR HTTP response must be JSON") from e
    text = str(data.get("text") or "").strip()
    raw_seg = data.get("segments")
    if isinstance(raw_seg, list) and raw_seg:
        segments = [dict(x) for x in raw_seg if isinstance(x, dict)]
    else:
        segments = [{"start": 0.0, "end": 0.0, "text": text or "(empty)"}]
    return text or "(empty)", segments, int((time.perf_counter() - t0) * 1000)


async def run_asr_pipeline(
    request: JobRequest,
    settings: Settings,
    inference: InferenceBackend,
    *,
    from_video: bool,
) -> AsrPipelineResult:
    t0 = time.perf_counter()
    uri = _first_media_uri(request.inputs, "video" if from_video else "audio")
    path, temps = await materialize_uri(uri, settings)
    try:
        wav = await asyncio.to_thread(media_to_wav_mono16k, path)
        ingest_ms = int((time.perf_counter() - t0) * 1000)
        transcript, segments, asr_ms = await transcribe_wav_bytes(wav, settings)
        user_q = _pick_user_question(request.inputs)
        llm_ms = 0
        llm_model: str | None = None
        p_hint: int | None = None
        e_hint: int | None = None
        if user_q:
            t1 = time.perf_counter()
            answer, llm_body = await llm_answer_from_evidence(
                inference,
                settings.llm_model,
                evidence_title="transcript",
                evidence_text=transcript,
                user_question=user_q,
                output_schema=request.output_schema,
            )
            llm_ms = int((time.perf_counter() - t1) * 1000)
            llm_model = settings.llm_model
            p_hint, e_hint = merge_token_hints(llm_body)
        else:
            answer = transcript
        return AsrPipelineResult(
            answer=answer,
            transcript=transcript,
            segments=segments,
            ingest_ms=ingest_ms,
            asr_ms=asr_ms,
            llm_ms=llm_ms,
            segment_count=len(segments),
            llm_model=llm_model,
            prompt_tokens_hint=p_hint,
            eval_tokens_hint=e_hint,
        )
    finally:
        for p in temps:
            p.unlink(missing_ok=True)
