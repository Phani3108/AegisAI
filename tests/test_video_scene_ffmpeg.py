from __future__ import annotations

from pathlib import Path

import pytest

from aegisai.pipelines.video import extract_keyframes
from aegisai.schemas.video import SamplingPolicy


def test_scene_mode_uses_ffmpeg_scene_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vid = tmp_path / "x.mp4"
    vid.write_bytes(b"x")
    out = tmp_path / "frames"
    out.mkdir()

    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs):
        captured.append(cmd)
        class _P:
            returncode = 0
            stderr = ""
            stdout = ""

        return _P()

    monkeypatch.setattr("aegisai.pipelines.video.shutil.which", lambda _: "/bin/ffmpeg")
    monkeypatch.setattr("aegisai.pipelines.video.subprocess.run", fake_run)
    (out / "frame_0001.png").write_bytes(b"\x89PNG")

    pol = SamplingPolicy(
        max_frames=6,
        scene_detection=True,
        scene_threshold=0.42,
    )
    extract_keyframes(vid, pol, out)
    assert captured
    cmd = captured[0]
    assert "-vsync" in cmd
    assert "vfr" in cmd
    assert any("gt(scene,0.42)" in a for a in cmd)
