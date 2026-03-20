from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(autouse=True)
def reset_isolation() -> None:
    from aegisai.services import job_store, metrics
    from aegisai.services.job_concurrency import reset_limiter_for_tests

    asyncio.run(metrics.reset_for_tests())
    asyncio.run(job_store.reset_test_state())
    reset_limiter_for_tests(8)
    yield
