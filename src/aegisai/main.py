from contextlib import asynccontextmanager

import chromadb
import httpx
from fastapi import FastAPI

from aegisai.api.openapi_extra import OPENAPI_TAGS
from aegisai.api.routes import (
    health,
    ops_metrics,
    v1_collections,
    v1_jobs,
    v1_metrics,
    v1_query,
    v1_stream,
)
from aegisai.config import get_settings
from aegisai.logging_json import configure_logging
from aegisai.middleware.api_key import APIKeyMiddleware
from aegisai.middleware.rate_limit import RateLimitMiddleware
from aegisai.middleware.request_id import RequestIdMiddleware
from aegisai.policy.loader import load_routing_policy
from aegisai.services import redis_util
from aegisai.services.job_concurrency import configure_limiter
from aegisai.services.job_recovery import resume_incomplete_jobs
from aegisai.telemetry.otel import maybe_instrument

_cfg0 = get_settings()
configure_logging(json_lines=_cfg0.log_json)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_limiter(settings.max_concurrent_jobs)
    policy = load_routing_policy(settings)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir.resolve()))
    rc = None
    if settings.redis_url:
        try:
            import redis.asyncio as aioredis
        except ImportError as e:
            raise RuntimeError(
                "AEGISAI_REDIS_URL is set; install aegisai[redis] (pip install 'aegisai[redis]')."
            ) from e
        rc = aioredis.from_url(settings.redis_url, decode_responses=True)
        redis_util.set_redis_client(rc)
    try:
        async with httpx.AsyncClient() as client:
            app.state.settings = settings
            app.state.http = client
            app.state.policy = policy
            app.state.chroma = chroma_client
            await resume_incomplete_jobs(app)
            yield
    finally:
        if rc is not None:
            await rc.aclose()
            redis_util.set_redis_client(None)


app = FastAPI(
    title="AegisAI",
    description=(
        "Local-first multimodal API — vision, video, RAG, policy-gated routing. "
        "See **`README.md`** (five-minute path) and **`tasks.md`** for capabilities."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(health.router, tags=["health"])
app.include_router(ops_metrics.router, tags=["metrics"])
app.include_router(v1_jobs.router, prefix="/v1", tags=["jobs"])
app.include_router(v1_collections.router, prefix="/v1", tags=["collections"])
app.include_router(v1_stream.router, prefix="/v1", tags=["stream"])
app.include_router(v1_query.router, prefix="/v1", tags=["query"])
app.include_router(v1_metrics.router, prefix="/v1", tags=["metrics"])

maybe_instrument(app, _cfg0.otel_enabled)
