"""P21: audio_ref jobs + video_transcribe (ASR path; ffmpeg monkeypatched in tests)."""

from __future__ import annotations

import io
import wave

import pytest
from fastapi.testclient import TestClient

from aegisai.main import app


def _minimal_wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 400)
    return buf.getvalue()


@pytest.fixture
def wav_file(tmp_path):
    p = tmp_path / "clip.wav"
    p.write_bytes(_minimal_wav())
    return p


def test_video_transcribe_without_video_is_422() -> None:
    with TestClient(app) as client:
        r = client.post(
            "/v1/jobs",
            json={
                "inputs": [{"type": "text", "text": "q"}],
                "video_transcribe": True,
                "mode": "local_only",
                "sensitivity_label": "internal",
            },
        )
        assert r.status_code == 422


def test_audio_ref_job_stub_asr(
    wav_file,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "aegisai.pipelines.asr_pipeline.media_to_wav_mono16k",
        lambda _p: _minimal_wav(),
    )
    uri = wav_file.resolve().as_uri()
    with TestClient(app) as client:
        r = client.post(
            "/v1/jobs",
            json={
                "inputs": [{"type": "audio_ref", "uri": uri}],
                "mode": "local_only",
                "sensitivity_label": "internal",
            },
        )
        assert r.status_code == 200
        jid = r.json()["job_id"]
        st: dict = {}
        for _ in range(80):
            st = client.get(f"/v1/jobs/{jid}").json()
            if st.get("status") in ("succeeded", "failed"):
                break
        assert st.get("status") == "succeeded"
        evs = st.get("events") or []
        assert any(e.get("stage") == "asr" for e in evs)
        pay = next(e.get("payload") for e in evs if e.get("stage") == "asr")
        assert pay and "segments" in pay


def test_video_transcribe_job_stub(
    wav_file,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use .wav as video path; ffmpeg path is bypassed via monkeypatch."""
    monkeypatch.setattr(
        "aegisai.pipelines.asr_pipeline.media_to_wav_mono16k",
        lambda _p: _minimal_wav(),
    )
    uri = wav_file.resolve().as_uri()
    with TestClient(app) as client:
        r = client.post(
            "/v1/jobs",
            json={
                "inputs": [{"type": "video_ref", "uri": uri}],
                "video_transcribe": True,
                "mode": "local_only",
                "sensitivity_label": "internal",
            },
        )
        assert r.status_code == 200
        jid = r.json()["job_id"]
        st: dict = {}
        for _ in range(80):
            st = client.get(f"/v1/jobs/{jid}").json()
            if st.get("status") in ("succeeded", "failed"):
                break
        assert st.get("status") == "succeeded"
        structured = (st.get("result") or {}).get("structured") or {}
        assert structured.get("transcribe_mode") == "video_audio"
