from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI

from aegisai.inference.protocol import InferenceBackend
from aegisai.services import job_store
from aegisai.services.job_runner import execute_job

logger = logging.getLogger(__name__)


async def resume_incomplete_jobs(app: FastAPI) -> None:
    settings = app.state.settings
    inference: InferenceBackend = app.state.inference
    chroma: Any = getattr(app.state, "chroma", None)
    pending = await job_store.list_recoverable_jobs()
    if not pending:
        return
    logger.info("job_recovery pending=%s", len(pending))
    # Stagger resumes to reduce burst load on startup.
    for jid in pending:
        req = await job_store.get_job_request(jid)
        if req is None:
            continue
        asyncio.create_task(execute_job(jid, req, settings, inference, chroma))
        await asyncio.sleep(0.02)
