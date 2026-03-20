import logging
from contextlib import asynccontextmanager

import chromadb
import httpx
from fastapi import FastAPI

from aegisai.api.routes import health, v1_collections, v1_jobs, v1_stream
from aegisai.config import get_settings
from aegisai.middleware.request_id import RequestIdMiddleware
from aegisai.policy.loader import load_routing_policy
from aegisai.telemetry.otel import maybe_instrument

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
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

app.include_router(health.router, tags=["health"])
app.include_router(v1_jobs.router, prefix="/v1", tags=["jobs"])
app.include_router(v1_collections.router, prefix="/v1", tags=["collections"])
app.include_router(v1_stream.router, prefix="/v1", tags=["stream"])

_cfg = get_settings()
maybe_instrument(app, _cfg.otel_enabled)
