import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

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
from aegisai.services.job_runner import execute_job

logger = logging.getLogger(__name__)

router = APIRouter()


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

    job_id = str(uuid.uuid4())
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
    _ = idempotency_key

    req_id = getattr(request.state, "request_id", None)
    logger.info(
        "job_create job_id=%s request_id=%s mode=%s label=%s",
        job_id,
        req_id,
        body.mode,
        body.sensitivity_label,
    )

    settings = request.app.state.settings
    http = request.app.state.http
    chroma = getattr(request.app.state, "chroma", None)
    background_tasks.add_task(execute_job, job_id, body, settings, http, chroma)

    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
