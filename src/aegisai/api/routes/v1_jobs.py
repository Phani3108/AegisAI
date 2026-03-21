import asyncio
import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse

from aegisai.api.openapi_extra import common_error_responses
from aegisai.config import Settings, get_settings
from aegisai.dlp.scan import scan_request_text
from aegisai.inference.protocol import InferenceBackend
from aegisai.middleware.ws_auth import websocket_shared_secret_authorized
from aegisai.policy.routing import RoutingPolicy
from aegisai.schemas.jobs import (
    InputType,
    JobCreateResponse,
    JobEvent,
    JobRequest,
    JobStatus,
    JobStatusResponse,
)
from aegisai.services import job_store, metrics
from aegisai.services.job_cancel import request_cancel
from aegisai.services.job_concurrency import get_limiter
from aegisai.services.job_runner import execute_job
from aegisai.services.readiness import readiness_details

logger = logging.getLogger(__name__)

router = APIRouter()


def _request_hash(body: JobRequest) -> str:
    canonical = json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_transient_error(err: str) -> bool:
    e = (err or "").lower()
    keys = ("timeout", "tempor", "connection", "503", "502", "network")
    return any(k in e for k in keys)


async def _execute_job_guarded(
    job_id: str,
    body: JobRequest,
    settings: Settings,
    inference: InferenceBackend,
    chroma: Any,
) -> None:
    try:
        max_attempts = int(settings.job_retry_attempts) + 1
        for attempt in range(1, max_attempts + 1):
            await job_store.increment_attempt(job_id)
            await execute_job(job_id, body, settings, inference, chroma)
            cur = await job_store.get_job(job_id)
            if cur is None or cur.status != JobStatus.failed:
                return
            if not _is_transient_error(cur.error or ""):
                return
            if attempt >= max_attempts:
                now = _utcnow()
                cur2 = await job_store.get_job(job_id)
                if cur2 is not None:
                    await job_store.patch_job(
                        job_id,
                        events=cur2.events
                        + [
                            JobEvent(
                                ts=now,
                                stage="pipeline",
                                message="dead-letter after retries exhausted",
                                route=cur2.route,
                            )
                        ],
                    )
                await job_store.mark_dead_letter(job_id)
                await metrics.record_job_dead_letter()
                return
            await metrics.record_job_retried()
            now = _utcnow()
            cur2 = await job_store.get_job(job_id)
            if cur2 is not None:
                await job_store.patch_job(
                    job_id,
                    status=JobStatus.queued,
                    updated_at=now,
                    events=cur2.events
                    + [JobEvent(ts=now, stage="pipeline", message="retrying transient failure")],
                )
            await asyncio.sleep(0.25 * attempt)
    finally:
        await get_limiter().release()


def _utcnow() -> datetime:
    return datetime.now(UTC)


@router.get(
    "/ready",
    summary="Readiness (authenticated)",
    description="Same checks as `GET /ready` when `AEGISAI_API_KEY` is set.",
    responses={**common_error_responses(401, 503)},
)
async def ready_v1(request: Request) -> dict[str, object]:
    """Same as GET /ready but under /v1 (requires API key when AEGISAI_API_KEY is set)."""
    settings = request.app.state.settings
    inference = request.app.state.inference
    try:
        return await readiness_details(settings, inference)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"not ready: {e!s}") from e


@router.get(
    "/policy",
    summary="Effective routing policy",
    description="Active hybrid routing rules (YAML-backed; see `config/routing_policy.yaml`).",
    responses={**common_error_responses(401)},
)
async def effective_routing_policy(request: Request) -> dict:
    """Active hybrid routing rules (YAML-backed; see config/routing_policy.yaml)."""
    policy: RoutingPolicy = request.app.state.policy
    return policy.public_view()


@router.post(
    "/jobs",
    response_model=JobCreateResponse,
    summary="Create async job",
    description=(
        "Queue an image/video/RAG job. Optional **Idempotency-Key** for safe retries. "
        "Set **AEGISAI_REDIS_URL** and install **aegisai[redis]** for multi-replica idempotency."
    ),
    responses={**common_error_responses(400, 401, 429, 500)},
)
async def create_job(
    request: Request,
    background_tasks: BackgroundTasks,  # kept for API compatibility
    body: JobRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobCreateResponse:
    policy: RoutingPolicy = request.app.state.policy
    roles = [str(x) for x in (getattr(request.state, "user_roles", None) or [])]
    if body.mode == "hybrid" and not policy.allows_hybrid_for_roles(body.sensitivity_label, roles):
        raise HTTPException(
            status_code=400,
            detail=(
                "hybrid mode is not allowed for this sensitivity label under the active "
                f"routing policy ({body.sensitivity_label!s}); see GET /v1/policy"
            ),
        )

    cfg = get_settings()
    if cfg.dlp_enabled and body.mode == "hybrid":
        text_blob = "\n".join(
            (inp.text or "") for inp in body.inputs if inp.type == InputType.text
        )
        dlp = scan_request_text(text_blob)
        if dlp.has_findings and cfg.dlp_block_hybrid:
            raise HTTPException(
                status_code=400,
                detail=(
                    "dlp: sensitive patterns detected in text inputs; "
                    "use local_only or remove sensitive content"
                ),
            )

    idem_key = ((idempotency_key or "").strip()[:256] or None)
    req_hash = _request_hash(body)
    if idem_key:
        existing_id = await job_store.idempotency_get(idem_key)
        if existing_id:
            old_hash = await job_store.idempotency_get_request_hash(idem_key)
            if old_hash and old_hash != req_hash:
                raise HTTPException(
                    status_code=409,
                    detail="idempotency key reuse with different request payload",
                )
            job = await job_store.get_job(existing_id)
            if job is None:
                raise HTTPException(
                    status_code=500,
                    detail="idempotency key maps to missing job",
                )
            return JobCreateResponse(job_id=existing_id, status=job.status)

    limiter = get_limiter()
    if not await limiter.acquire():
        raise HTTPException(
            status_code=429,
            detail="too many concurrent jobs; retry later",
        )

    job_id = str(uuid.uuid4())
    settings = request.app.state.settings
    inference = request.app.state.inference
    chroma = getattr(request.app.state, "chroma", None)

    try:
        if idem_key:
            prev = await job_store.idempotency_put_if_absent(idem_key, job_id, req_hash)
            if prev is not None:
                await limiter.release()
                job = await job_store.get_job(prev)
                if job is None:
                    raise HTTPException(
                        status_code=500,
                        detail="idempotency key maps to missing job",
                    )
                return JobCreateResponse(job_id=prev, status=job.status)

        now = _utcnow()
        route = "local_only" if body.mode == "local_only" else "hybrid"
        policy_event = JobEvent(
            ts=now,
            stage="policy",
            message=(
                f"routing_policy_v{policy.version} label={body.sensitivity_label} "
                f"mode={body.mode} route={route} force_local_only={policy.force_local_only}"
            ),
            route=route,
        )
        await job_store.set_job_with_request(
            job_id,
            JobStatusResponse(
                job_id=job_id,
                status=JobStatus.queued,
                created_at=now,
                updated_at=now,
                route=route,
                events=[policy_event],
                result=None,
                error=None,
            ),
            body,
        )
    except Exception:
        if idem_key:
            await job_store.idempotency_delete(idem_key)
        await limiter.release()
        raise

    req_id = getattr(request.state, "request_id", None)
    logger.info(
        "job_create job_id=%s request_id=%s mode=%s label=%s",
        job_id,
        req_id,
        body.mode,
        body.sensitivity_label,
    )

    background_tasks.add_task(_execute_job_guarded, job_id, body, settings, inference, chroma)

    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    responses={**common_error_responses(401, 404)},
)
async def get_job(job_id: str) -> JobStatusResponse:
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post(
    "/jobs/{job_id}/cancel",
    summary="Request job cancellation",
    responses={**common_error_responses(401, 404)},
)
async def cancel_job(job_id: str) -> dict[str, Any]:
    """Request cooperative cancellation; the worker observes before heavy pipeline steps."""
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status in (JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled):
        return {
            "job_id": job_id,
            "status": job.status.value,
            "cancel_requested": False,
        }
    await request_cancel(job_id)
    return {
        "job_id": job_id,
        "status": job.status.value,
        "cancel_requested": True,
    }


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_events(websocket: WebSocket, job_id: str) -> None:
    """WS stream of job events (poll); ends with type ``done`` (same idea as SSE)."""
    settings_ws: Settings = websocket.app.state.settings
    if not websocket_shared_secret_authorized(websocket, settings_ws.api_key):
        await websocket.close(code=4401, reason="unauthorized")
        return
    await websocket.accept()
    try:
        last_n = 0
        while True:
            job = await job_store.get_job(job_id)
            if job is None:
                await websocket.send_json({"type": "error", "detail": "not_found"})
                break
            if len(job.events) > last_n:
                for ev in job.events[last_n:]:
                    await websocket.send_json(
                        {"type": "event", "data": ev.model_dump(mode="json")}
                    )
                last_n = len(job.events)
            if job.status in (
                JobStatus.succeeded,
                JobStatus.failed,
                JobStatus.cancelled,
            ):
                await websocket.send_json({"type": "done", "status": job.status.value})
                break
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass


@router.get("/jobs/{job_id}/events")
async def stream_job_events(job_id: str) -> StreamingResponse:
    """SSE stream of new `JobEvent` rows until the job reaches a terminal status (poll-based)."""

    async def gen():
        last_n = 0
        while True:
            job = await job_store.get_job(job_id)
            if job is None:
                yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                break
            if len(job.events) > last_n:
                for ev in job.events[last_n:]:
                    yield f"data: {json.dumps(ev.model_dump(mode='json'), default=str)}\n\n"
                last_n = len(job.events)
            if job.status in (
                JobStatus.succeeded,
                JobStatus.failed,
                JobStatus.cancelled,
            ):
                yield "data: [DONE]\n\n"
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get(
    "/jobs/{job_id}/audit",
    response_model=None,
    summary="Export job audit events",
    responses={**common_error_responses(401, 404)},
)
async def get_job_audit(
    job_id: str,
    format: str | None = Query(default=None, description="`ndjson` for newline-delimited JSON."),
) -> Response | list[dict[str, Any]]:
    """Export append-only job events for SIEM / audit (no raw media)."""
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    events = [e.model_dump(mode="json") for e in job.events]
    if format == "ndjson":
        body = "\n".join(json.dumps(ev, default=str) for ev in events)
        if body:
            body += "\n"
        return Response(content=body, media_type="application/x-ndjson")
    return events
