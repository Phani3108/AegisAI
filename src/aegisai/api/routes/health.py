from importlib.metadata import PackageNotFoundError, version

import httpx
from fastapi import APIRouter, HTTPException, Request

from aegisai.api.openapi_extra import common_error_responses
from aegisai.services.readiness import readiness_details

router = APIRouter()


@router.get("/health", summary="Health check", description="Returns static OK (legacy alias).")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/live",
    summary="Liveness probe",
    description="Process is up; no dependency checks. Use as Kubernetes `livenessProbe`.",
)
def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description=(
        "Ollama reachable and Chroma persist dir writable. Unauthenticated; "
        "use as Kubernetes `readinessProbe`."
    ),
    responses={**common_error_responses(503)},
)
async def ready(request: Request) -> dict[str, object]:
    """Readiness: Ollama + Chroma dir; no API key (use as kube readinessProbe)."""
    settings = request.app.state.settings
    http: httpx.AsyncClient = request.app.state.http
    try:
        return await readiness_details(settings, http)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"not ready: {e!s}") from e


@router.get("/version", summary="Package version", description="Installed distribution version.")
def app_version() -> dict[str, str]:
    """Package version (from installed distribution); falls back for dev trees without metadata."""
    try:
        ver = version("aegisai")
    except PackageNotFoundError:
        ver = "0.1.0-dev"
    return {"name": "aegisai", "version": ver}
