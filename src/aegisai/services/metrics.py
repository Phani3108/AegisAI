from __future__ import annotations

import asyncio
from typing import Any

from aegisai.schemas.jobs import InputType, JobRequest, LatencyBreakdownMs

_lock = asyncio.Lock()

_state: dict[str, Any] = {
    "jobs_completed_total": 0,
    "jobs_failed_total": 0,
    "jobs_cancelled_total": 0,
    "by_pipeline": {},
    "latency_ms_sum": 0,
    "latency_ms_count": 0,
}


class Pipeline:
    chroma_rag = "chroma_rag"
    ephemeral_rag = "ephemeral_rag"
    image = "image"
    video = "video"


def _ensure_pipeline(name: str) -> dict[str, int]:
    bp = _state["by_pipeline"]
    if name not in bp:
        bp[name] = {"completed": 0, "failed": 0, "cancelled": 0}
    return bp[name]


async def record_job_completed(pipeline: str, total_latency_ms: int | None = None) -> None:
    async with _lock:
        _state["jobs_completed_total"] += 1
        p = _ensure_pipeline(pipeline)
        p["completed"] += 1
        if total_latency_ms is not None and total_latency_ms >= 0:
            _state["latency_ms_sum"] += int(total_latency_ms)
            _state["latency_ms_count"] += 1


async def record_job_failed(pipeline: str) -> None:
    async with _lock:
        _state["jobs_failed_total"] += 1
        p = _ensure_pipeline(pipeline)
        p["failed"] += 1


async def record_job_cancelled(pipeline: str) -> None:
    async with _lock:
        _state["jobs_cancelled_total"] += 1
        p = _ensure_pipeline(pipeline)
        p["cancelled"] += 1


async def reset_for_tests() -> None:
    """Reset counters (intended for pytest)."""
    async with _lock:
        _state["jobs_completed_total"] = 0
        _state["jobs_failed_total"] = 0
        _state["jobs_cancelled_total"] = 0
        _state["by_pipeline"] = {}
        _state["latency_ms_sum"] = 0
        _state["latency_ms_count"] = 0


async def snapshot() -> dict[str, Any]:
    from aegisai.services.job_concurrency import get_limiter

    async with _lock:
        avg = None
        if _state["latency_ms_count"] > 0:
            avg = _state["latency_ms_sum"] / _state["latency_ms_count"]
        return {
            "jobs_completed_total": _state["jobs_completed_total"],
            "jobs_failed_total": _state["jobs_failed_total"],
            "jobs_cancelled_total": _state["jobs_cancelled_total"],
            "by_pipeline": {k: dict(v) for k, v in _state["by_pipeline"].items()},
            "latency_ms_avg": avg,
            "latency_ms_observations": _state["latency_ms_count"],
            "jobs_in_flight": get_limiter().in_flight,
        }


def latency_total_ms(lat: LatencyBreakdownMs | None) -> int | None:
    if lat is None:
        return None
    acc = 0
    for field in ("ingest_ms", "vision_ms", "llm_ms", "retrieval_ms"):
        v = getattr(lat, field, None)
        if isinstance(v, int):
            acc += v
    return acc if acc > 0 else None


def infer_pipeline_kind(body: JobRequest) -> str:
    if body.rag_collection and str(body.rag_collection).strip():
        return Pipeline.chroma_rag
    if any(i.type == InputType.video_ref for i in body.inputs):
        return Pipeline.video
    if any(i.type == InputType.document_ref for i in body.inputs):
        return Pipeline.ephemeral_rag
    if any(i.type == InputType.image_ref for i in body.inputs):
        return Pipeline.image
    return "unknown"


def render_prometheus(snap: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# HELP aegisai_jobs_completed_total Completed async jobs.")
    lines.append("# TYPE aegisai_jobs_completed_total counter")
    lines.append(f"aegisai_jobs_completed_total {snap['jobs_completed_total']}")
    lines.append("# HELP aegisai_jobs_failed_total Failed async jobs.")
    lines.append("# TYPE aegisai_jobs_failed_total counter")
    lines.append(f"aegisai_jobs_failed_total {snap['jobs_failed_total']}")
    lines.append("# HELP aegisai_jobs_cancelled_total Cancelled async jobs.")
    lines.append("# TYPE aegisai_jobs_cancelled_total counter")
    lines.append(f"aegisai_jobs_cancelled_total {snap.get('jobs_cancelled_total', 0)}")
    for pipe, d in snap.get("by_pipeline", {}).items():
        safe = pipe.replace("\\", "_").replace('"', "_")
        lines.append(
            f'aegisai_jobs_completed_by_pipeline{{pipeline="{safe}"}} {d.get("completed", 0)}'
        )
        lines.append(
            f'aegisai_jobs_failed_by_pipeline{{pipeline="{safe}"}} {d.get("failed", 0)}'
        )
        lines.append(
            f'aegisai_jobs_cancelled_by_pipeline{{pipeline="{safe}"}} {d.get("cancelled", 0)}'
        )
    avg = snap.get("latency_ms_avg")
    if avg is not None:
        lines.append(
            "# HELP aegisai_job_latency_ms_avg Rolling average of summed stage latencies (ms)."
        )
        lines.append("# TYPE aegisai_job_latency_ms_avg gauge")
        lines.append(f"aegisai_job_latency_ms_avg {float(avg):.6f}")
    inflight = snap.get("jobs_in_flight")
    if inflight is not None:
        lines.append("# HELP aegisai_jobs_in_flight Jobs accepted but pipeline not finished yet.")
        lines.append("# TYPE aegisai_jobs_in_flight gauge")
        lines.append(f"aegisai_jobs_in_flight {int(inflight)}")
    return "\n".join(lines) + "\n"
