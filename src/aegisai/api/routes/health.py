from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/version")
def app_version() -> dict[str, str]:
    """Package version (from installed distribution); falls back for dev trees without metadata."""
    try:
        ver = version("aegisai")
    except PackageNotFoundError:
        ver = "0.1.0-dev"
    return {"name": "aegisai", "version": ver}
