from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(autouse=True)
def reset_metrics() -> None:
    from aegisai.services import metrics

    asyncio.run(metrics.reset_for_tests())
    yield
