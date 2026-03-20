from __future__ import annotations

import json
from typing import Any

import httpx

from aegisai.config import Settings
from aegisai.ollama.client import OllamaClient
from aegisai.pipelines.image import run_image_pipeline
from aegisai.pipelines.rag import run_rag_pipeline
from aegisai.pipelines.rag_chroma import run_chroma_rag_pipeline
from aegisai.pipelines.video_job import run_video_pipeline
from aegisai.schemas.jobs import (
    InputType,
    JobEvent,
    JobRequest,
    JobResult,
    JobStatus,
    JobStatusResponse,
    LatencyBreakdownMs,
)
from aegisai.services import job_cancel, job_store, metrics


def _has_input(body: JobRequest, t: InputType) -> bool:
    return any(i.type == t for i in body.inputs)


def _has_rag_collection(body: JobRequest) -> bool:
    return bool((body.rag_collection or "").strip())


def _media_conflict(body: JobRequest) -> bool:
    n = sum(
        1
        for t in (InputType.video_ref, InputType.image_ref, InputType.document_ref)
        if _has_input(body, t)
    )
    return n > 1


async def _record_success(body: JobRequest, latency: LatencyBreakdownMs | None) -> None:
    await metrics.record_job_completed(
        metrics.infer_pipeline_kind(body),
        metrics.latency_total_ms(latency),
    )


def _structured_with_optional_json(
    body: JobRequest,
    answer_text: str,
    base: dict[str, Any],
) -> dict[str, Any]:
    out = dict(base)
    if body.output_schema:
        out["json_mode"] = True
        try:
            out["parsed"] = json.loads(answer_text)
        except json.JSONDecodeError:
            out["parse_error"] = "invalid_json"
    return out


async def _apply_client_cancel(
    job_id: str,
    body: JobRequest,
    route: str,
    fallback: JobStatusResponse,
) -> None:
    await job_cancel.clear(job_id)
    now = job_store.utcnow()
    curj = (await job_store.get_job(job_id)) or fallback
    await job_store.patch_job(
        job_id,
        status=JobStatus.cancelled,
        updated_at=now,
        events=curj.events
        + [
            JobEvent(
                ts=now,
                stage="pipeline",
                message="cancelled by client",
                route=route,
            )
        ],
    )
    await metrics.record_job_cancelled(metrics.infer_pipeline_kind(body))


async def _cancel_if_requested(
    job_id: str,
    body: JobRequest,
    route: str,
    fallback: JobStatusResponse,
) -> bool:
    if not await job_cancel.is_requested(job_id):
        return False
    await _apply_client_cancel(job_id, body, route, fallback)
    return True


async def execute_job(
    job_id: str,
    body: JobRequest,
    settings: Settings,
    http: httpx.AsyncClient,
    chroma: Any,
) -> None:
    now = job_store.utcnow()
    cur = await job_store.get_job(job_id)
    if cur is None:
        return
    route = cur.route

    if await _cancel_if_requested(job_id, body, route, cur):
        return

    await job_store.patch_job(
        job_id,
        status=JobStatus.running,
        updated_at=now,
        events=cur.events
        + [
            JobEvent(
                ts=now,
                stage="pipeline",
                message="started",
                route=route,
            )
        ],
    )

    if body.mode == "hybrid":
        cur2 = (await job_store.get_job(job_id)) or cur
        await job_store.patch_job(
            job_id,
            events=cur2.events
            + [
                JobEvent(
                    ts=job_store.utcnow(),
                    stage="policy",
                    message="hybrid mode requested; Phase 0 runs local inference only",
                    route=route,
                )
            ],
        )

    if await _cancel_if_requested(
        job_id,
        body,
        route,
        (await job_store.get_job(job_id)) or cur,
    ):
        return

    ollama = OllamaClient(settings.ollama_base_url, http, timeout_s=settings.ollama_timeout_s)

    try:
        if await _cancel_if_requested(
            job_id,
            body,
            route,
            (await job_store.get_job(job_id)) or cur,
        ):
            return

        if _has_rag_collection(body):
            if chroma is None:
                raise RuntimeError("Chroma client unavailable")
            result = await run_chroma_rag_pipeline(body, settings, ollama, chroma)
            done = job_store.utcnow()
            cur3 = (await job_store.get_job(job_id)) or cur
            latency = LatencyBreakdownMs(
                ingest_ms=result.ingest_ms,
                retrieval_ms=result.retrieval_ms,
                llm_ms=result.llm_ms,
            )
            coll = (body.rag_collection or "").strip()
            await job_store.patch_job(
                job_id,
                status=JobStatus.succeeded,
                updated_at=done,
                result=JobResult(
                    text=result.answer,
                    structured=_structured_with_optional_json(
                        body,
                        result.answer,
                        {
                            "collection": coll,
                            "chunk_count": result.chunk_count,
                            "embed_model": result.embed_model,
                            "store": "chroma",
                        },
                    ),
                ),
                events=cur3.events
                + [
                    JobEvent(
                        ts=done,
                        stage="pipeline",
                        message="succeeded",
                        route=route,
                        models_used=[result.embed_model, result.llm_model],
                        latency=latency,
                    )
                ],
            )
            await _record_success(body, latency)
            return

        if _media_conflict(body):
            raise ValueError("use only one of video_ref, image_ref, document_ref per job")

        if await _cancel_if_requested(
            job_id,
            body,
            route,
            (await job_store.get_job(job_id)) or cur,
        ):
            return

        if _has_input(body, InputType.video_ref):
            result = await run_video_pipeline(
                body,
                settings,
                ollama,
                sampling=body.video_sampling,
            )
            done = job_store.utcnow()
            cur3 = (await job_store.get_job(job_id)) or cur
            latency = LatencyBreakdownMs(
                ingest_ms=result.ingest_ms,
                vision_ms=result.vision_ms,
                llm_ms=result.llm_ms,
            )
            await job_store.patch_job(
                job_id,
                status=JobStatus.succeeded,
                updated_at=done,
                result=JobResult(
                    text=result.answer,
                    structured=_structured_with_optional_json(
                        body,
                        result.answer,
                        {"frame_count": result.frame_count},
                    ),
                ),
                events=cur3.events
                + [
                    JobEvent(
                        ts=done,
                        stage="pipeline",
                        message="succeeded",
                        route=route,
                        models_used=[result.vision_model, result.llm_model],
                        latency=latency,
                    )
                ],
            )
            await _record_success(body, latency)
            return

        if await _cancel_if_requested(
            job_id,
            body,
            route,
            (await job_store.get_job(job_id)) or cur,
        ):
            return

        if _has_input(body, InputType.document_ref):
            result = await run_rag_pipeline(body, settings, ollama)
            done = job_store.utcnow()
            cur3 = (await job_store.get_job(job_id)) or cur
            latency = LatencyBreakdownMs(
                ingest_ms=result.ingest_ms,
                retrieval_ms=result.retrieval_ms,
                llm_ms=result.llm_ms,
            )
            await job_store.patch_job(
                job_id,
                status=JobStatus.succeeded,
                updated_at=done,
                result=JobResult(
                    text=result.answer,
                    structured=_structured_with_optional_json(
                        body,
                        result.answer,
                        {
                            "chunk_count": result.chunk_count,
                            "embed_model": result.embed_model,
                            "store": "ephemeral",
                        },
                    ),
                ),
                events=cur3.events
                + [
                    JobEvent(
                        ts=done,
                        stage="pipeline",
                        message="succeeded",
                        route=route,
                        models_used=[result.embed_model, result.llm_model],
                        latency=latency,
                    )
                ],
            )
            await _record_success(body, latency)
            return

        if await _cancel_if_requested(
            job_id,
            body,
            route,
            (await job_store.get_job(job_id)) or cur,
        ):
            return

        if not _has_input(body, InputType.image_ref):
            raise ValueError(
                "job needs image_ref, video_ref, document_ref, or rag_collection + text"
            )

        result = await run_image_pipeline(body, settings, ollama)
        done = job_store.utcnow()
        cur3 = (await job_store.get_job(job_id)) or cur
        latency = LatencyBreakdownMs(
            ingest_ms=result.ingest_ms,
            vision_ms=result.vision_ms,
            llm_ms=result.llm_ms,
        )
        await job_store.patch_job(
            job_id,
            status=JobStatus.succeeded,
            updated_at=done,
            result=JobResult(
                text=result.answer,
                structured=_structured_with_optional_json(body, result.answer, {}),
            ),
            events=cur3.events
            + [
                JobEvent(
                    ts=done,
                    stage="pipeline",
                    message="succeeded",
                    route=route,
                    models_used=[result.vision_model, result.llm_model],
                    latency=latency,
                )
            ],
        )
        await _record_success(body, latency)
    except Exception as e:
        if await job_cancel.is_requested(job_id):
            await _apply_client_cancel(
                job_id,
                body,
                route,
                (await job_store.get_job(job_id)) or cur,
            )
            return
        await metrics.record_job_failed(metrics.infer_pipeline_kind(body))
        failed = job_store.utcnow()
        cur4 = (await job_store.get_job(job_id)) or cur
        await job_store.patch_job(
            job_id,
            status=JobStatus.failed,
            updated_at=failed,
            error=str(e),
            events=cur4.events
            + [
                JobEvent(
                    ts=failed,
                    stage="pipeline",
                    message=f"failed: {e!s}",
                    route=route,
                )
            ],
        )
