from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Response

from aegisai.services import metrics

router = APIRouter()


@router.get("/metrics", response_model=None)
async def metrics_endpoint(
    format: str | None = Query(default=None, description="Use `prometheus` for text exposition."),
) -> Response | dict[str, Any]:
    snap = await metrics.snapshot()
    if format == "prometheus":
        return Response(
            content=metrics.render_prometheus(snap),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    return snap
