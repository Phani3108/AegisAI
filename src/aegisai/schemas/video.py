from pydantic import BaseModel, Field


class SamplingPolicy(BaseModel):
    """Caps work for video: extract up to max_frames stills."""

    max_frames: int = Field(default=8, ge=1, le=64)
    fps: float | None = Field(
        default=None,
        gt=0,
        description="If set, passed to ffmpeg fps filter (e.g. 0.5 => one frame every 2s).",
    )
    scene_detection: bool = Field(
        default=False,
        description="Use ffmpeg scene cuts (select=gt(scene,...)); ignores fps when True.",
    )
    scene_threshold: float = Field(
        default=0.35,
        ge=0.1,
        le=0.9,
        description="Scene change score threshold for ffmpeg select filter (higher = fewer cuts).",
    )
