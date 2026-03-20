from __future__ import annotations

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def maybe_instrument(app: FastAPI, enabled: bool) -> None:
    if not enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "AEGISAI_OTEL_ENABLED is true but optional OTEL packages are missing; "
            "install with: pip install 'aegisai[otel]'"
        )
        return

    resource = Resource.create({"service.name": "aegisai"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    logger.info("OpenTelemetry FastAPI instrumentation enabled (OTLP HTTP exporter)")
