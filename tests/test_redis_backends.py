"""Redis-backed idempotency and rate limiting (optional extra + fakeredis in tests)."""

from __future__ import annotations

import pytest

from aegisai.middleware.rate_limit import _redis_sliding_window_allow
from aegisai.services import job_store
from aegisai.services.redis_util import set_redis_client


@pytest.fixture
async def fake_redis():
    pytest.importorskip("fakeredis")
    from fakeredis import FakeAsyncRedis

    r = FakeAsyncRedis(decode_responses=True)
    set_redis_client(r)
    yield r
    await r.aclose()
    set_redis_client(None)


@pytest.mark.anyio
async def test_idempotency_redis_put_if_absent(fake_redis) -> None:
    assert fake_redis is not None
    assert await job_store.idempotency_put_if_absent("idem-k", "job-a") is None
    assert await job_store.idempotency_put_if_absent("idem-k", "job-b") == "job-a"
    assert await job_store.idempotency_get("idem-k") == "job-a"
    await job_store.idempotency_delete("idem-k")
    assert await job_store.idempotency_get("idem-k") is None


@pytest.mark.anyio
async def test_idempotency_redis_get_miss(fake_redis) -> None:
    assert fake_redis is not None
    assert await job_store.idempotency_get("nope") is None


@pytest.mark.anyio
async def test_rate_limit_redis_window(fake_redis) -> None:
    client = "10.0.0.1"
    limit = 3
    for _ in range(limit):
        assert await _redis_sliding_window_allow(fake_redis, client, limit) is True
    assert await _redis_sliding_window_allow(fake_redis, client, limit) is False
