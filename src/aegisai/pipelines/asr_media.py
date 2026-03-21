"""ffmpeg helpers: normalize media to 16 kHz mono WAV for ASR (P21)."""

from __future__ import annotations

import io
import shutil
import subprocess
import wave
from pathlib import Path


def media_to_wav_mono16k(media_path: Path) -> bytes:
    """Decode arbitrary audio/video file to PCM WAV (16 kHz mono) via ffmpeg stdin/stdout."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH (required for audio/video ASR extract).")
    if not media_path.is_file():
        raise FileNotFoundError(media_path)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(media_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            "-",
        ],
        capture_output=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed: {err or proc.returncode}")
    return proc.stdout


def wav_duration_seconds(wav: bytes) -> float:
    try:
        with wave.open(io.BytesIO(wav), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            if rate <= 0:
                return 0.0
            return frames / float(rate)
    except Exception:
        return 0.0
