import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from aegisai.config import Settings
from aegisai.ollama.client import OllamaClient
from aegisai.policy.routing import RoutingPolicy
from aegisai.schemas.jobs import (
    JobCreateResponse,
    JobEvent,
    JobRequest,
    JobStatus,
    JobStatusResponse,
)
from aegisai.services import job_store
from aegisai.services.job_concurrency import get_limiter
from aegisai.services.job_runner import execute_job

logger = logging.getLogger(__name__)

router = APIRouter()


async def _execute_job_guarded(
    job_id: str,
    body: JobRequest,
    settings: Settings,
    http: httpx.AsyncClient,
    chroma: Any,
) -> None:
    try:
        await execute_job(job_id, body, settings, http, chroma)
    finally:
        await get_limiter().release()


def _utcnow() -> datetime:
    return datetime.now(UTC)


@router.get("/ready")
async def ready(request: Request) -> dict:
    """Returns 200 when Ollama responds to /api/tags; 503 otherwise."""
    settings = request.app.state.settings
    http = request.app.state.http
    ollama = OllamaClient(settings.ollama_base_url, http, timeout_s=10.0)
    try:
        data = await ollama.tags()
        names = [m.get("name", "") for m in data.get("models", [])]
        return {"ollama": "ok", "models": names}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ollama unavailable: {e!s}") from e


@router.get("/policy")
async def effective_routing_policy(request: Request) -> dict:
    """Active hybrid routing rules (YAML-backed; see config/routing_policy.yaml)."""
    policy: RoutingPolicy = request.app.state.policy
    return policy.public_view()


@router.post("/jobs", response_model=JobCreateResponse)
async def create_job(
    request: Request,
    background_tasks: BackgroundTasks,
    body: JobRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobCreateResponse:
    policy: RoutingPolicy = request.app.state.policy
    if body.mode == "hybrid" and not policy.allows_hybrid(body.sensitivity_label):
        raise HTTPException(
            status_code=400,
            detail=(
                "hybrid mode is not allowed for this sensitivity label under the active "
                f"routing policy ({body.sensitivity_label!s}); see GET /v1/policy"
            ),
        )

    idem_key = ((idempotency_key or "").strip()[:256] or None)
    if idem_key:
        existing_id = await job_store.idempotency_get(idem_key)
        if existing_id:
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
    http = request.app.state.http
    chroma = getattr(request.app.state, "chroma", None)

    try:
        if idem_key:
            prev = await job_store.idempotency_put_if_absent(idem_key, job_id)
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
        await job_store.set_job(
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

    background_tasks.add_task(_execute_job_guarded, job_id, body, settings, http, chroma)

    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
