from __future__ import annotations

from fastapi import APIRouter, Response

from aegisai.services import metrics

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus scrape endpoint",
    description="Unauthenticated when no API key; standard `text/plain` exposition format.",
)
async def prometheus_metrics() -> Response:
    """Prometheus scrape endpoint (OpenMetrics-compatible text)."""
    snap = await metrics.snapshot()
    return Response(
        content=metrics.render_prometheus(snap),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
