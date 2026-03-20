from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from aegisai.schemas.video import SamplingPolicy


class InputType(StrEnum):
    image_ref = "image_ref"
    video_ref = "video_ref"
    document_ref = "document_ref"
    text = "text"


class JobInput(BaseModel):
    """Single item the pipeline can consume."""

    type: InputType
    uri: str | None = Field(
        default=None,
        description="file:// or internal id; never send raw bytes in JSON for large media.",
    )
    text: str | None = None


class JobRequest(BaseModel):
    """
    OpenAPI-aligned job creation body.
    See planning.md: Policy before inference; mode drives routing stub.
    """

    inputs: list[JobInput] = Field(min_length=1)
    sensitivity_label: Literal["public", "internal", "confidential", "regulated"] = "internal"
    mode: Literal["local_only", "hybrid"] = "local_only"
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="Optional JSON Schema for structured model output.",
    )
    video_sampling: SamplingPolicy | None = Field(
        default=None,
        description="Keyframe caps for video_ref jobs; defaults apply when omitted.",
    )
    rag_collection: str | None = Field(
        default=None,
        description="Chroma collection for RAG-only jobs (needs text question; no media inputs).",
    )

    @field_validator("rag_collection", mode="before")
    @classmethod
    def _strip_rag_collection(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @model_validator(mode="after")
    def _rag_collection_rules(self) -> JobRequest:
        rc = self.rag_collection
        if not rc:
            return self
        for inp in self.inputs:
            if inp.type in (
                InputType.image_ref,
                InputType.video_ref,
                InputType.document_ref,
            ):
                raise ValueError(
                    "rag_collection cannot be combined with image_ref, video_ref, or document_ref"
                )
        if not any(
            inp.type == InputType.text and (inp.text or "").strip() for inp in self.inputs
        ):
            raise ValueError("rag_collection jobs require a non-empty text input (the question)")
        return self


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class LatencyBreakdownMs(BaseModel):
    ingest_ms: int | None = None
    vision_ms: int | None = None
    llm_ms: int | None = None
    retrieval_ms: int | None = None


class JobEvent(BaseModel):
    """Audit-oriented event; avoid embedding secrets or full payloads."""

    ts: datetime
    stage: str
    message: str
    route: str | None = None
    models_used: list[str] | None = None
    latency: LatencyBreakdownMs | None = None


class JobResult(BaseModel):
    text: str | None = None
    structured: dict[str, Any] | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    route: str
    events: list[JobEvent]
    result: JobResult | None
    error: str | None


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
