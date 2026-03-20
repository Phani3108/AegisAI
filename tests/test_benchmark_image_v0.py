from __future__ import annotations

import base64
from pathlib import Path

import pytest

from aegisai.benchmarks.image_v0 import run_image_benchmark

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def tiny_image(tmp_path: Path) -> Path:
    p = tmp_path / "b.png"
    p.write_bytes(_TINY_PNG)
    return p


@pytest.mark.asyncio
async def test_run_image_benchmark_shape(tiny_image: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class _Out:
        vision_model = "vm"
        llm_model = "lm"
        vision_ms = 10
        llm_ms = 20
        prompt_tokens_hint = 1
        eval_tokens_hint = 2
        answer = "benchmark answer"

    async def fake_pipeline(*_a, **_kw):
        return _Out()

    monkeypatch.setattr(
        "aegisai.benchmarks.image_v0.run_image_pipeline",
        fake_pipeline,
    )

    r = await run_image_benchmark(tiny_image, question="q?")
    assert r["vision_model"] == "vm"
    assert r["llm_model"] == "lm"
    assert r["vision_ms"] == 10
    assert r["llm_ms"] == 20
    assert r["wall_ms"] >= 0
    assert r["answer_preview"] == "benchmark answer"
