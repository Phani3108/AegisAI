from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from aegisai.schemas.video import SamplingPolicy


def extract_keyframes(video_path: Path, policy: SamplingPolicy, out_dir: Path) -> list[Path]:
    """
    Extract PNG frames into out_dir using ffmpeg.
    Requires ffmpeg on PATH. out_dir must exist.
    """
    if not video_path.is_file():
        raise FileNotFoundError(video_path)
    if not out_dir.is_dir():
        raise NotADirectoryError(out_dir)
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH; install ffmpeg to use video extraction.")

    pattern = str(out_dir / "frame_%04d.png")
    vf = f"fps={policy.fps}" if policy.fps is not None else "fps=1"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-frames:v",
        str(policy.max_frames),
        pattern,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {err or 'no stderr'}")
    return sorted(out_dir.glob("frame_*.png"))
