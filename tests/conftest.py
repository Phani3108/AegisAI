from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(autouse=True)
def chroma_persist_tmp(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test Chroma dir so default ./data/chroma does not break parallel/CI runs."""
    monkeypatch.setenv("AEGISAI_CHROMA_PERSIST_DIR", str(tmp_path / "chroma_data"))


@pytest.fixture(autouse=True)
def reset_isolation() -> None:
    from aegisai.middleware.rate_limit import reset_for_tests as reset_rate_limit_for_tests
    from aegisai.services import job_cancel, job_store, metrics
    from aegisai.services.job_concurrency import reset_limiter_for_tests
    from aegisai.services.redis_util import set_redis_client

    set_redis_client(None)
    asyncio.run(metrics.reset_for_tests())
    asyncio.run(reset_rate_limit_for_tests())
    asyncio.run(job_store.reset_test_state())
    asyncio.run(job_cancel.reset_for_tests())
    reset_limiter_for_tests(8)
    yield
