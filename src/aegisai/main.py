from contextlib import asynccontextmanager

import chromadb
import httpx
from fastapi import FastAPI

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
from aegisai.middleware.request_id import RequestIdMiddleware
from aegisai.policy.loader import load_routing_policy
from aegisai.services.job_concurrency import configure_limiter
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
    async with httpx.AsyncClient() as client:
        app.state.settings = settings
        app.state.http = client
        app.state.policy = policy
        app.state.chroma = chroma_client
        yield


app = FastAPI(
    title="AegisAI",
    description="Local multimodal stack — local-first inference and job API.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(APIKeyMiddleware)

app.include_router(health.router, tags=["health"])
app.include_router(ops_metrics.router, tags=["metrics"])
app.include_router(v1_jobs.router, prefix="/v1", tags=["jobs"])
app.include_router(v1_collections.router, prefix="/v1", tags=["collections"])
app.include_router(v1_stream.router, prefix="/v1", tags=["stream"])
app.include_router(v1_query.router, prefix="/v1", tags=["query"])
app.include_router(v1_metrics.router, prefix="/v1", tags=["metrics"])

maybe_instrument(app, _cfg0.otel_enabled)
