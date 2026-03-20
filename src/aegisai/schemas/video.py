from pydantic import BaseModel, Field


class SamplingPolicy(BaseModel):
    """Caps work for video: extract up to max_frames stills."""

    max_frames: int = Field(default=8, ge=1, le=64)
    fps: float | None = Field(
        default=None,
        gt=0,
        description="If set, passed to ffmpeg fps filter (e.g. 0.5 => one frame every 2s).",
    )
