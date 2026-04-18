# services/medkb/src/medkb/tracing.py
from __future__ import annotations

import functools
import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

_OTEL_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_AVAILABLE = True
except ImportError:
    trace = None  # type: ignore[assignment]
    logger.info("OpenTelemetry not available — tracing disabled")


SERVICE_NAME = "dhg-medkb"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENVIRONMENT", "production")


def init_tracing(endpoint: str) -> None:
    if not _OTEL_AVAILABLE:
        return

    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": SERVICE_VERSION,
            "deployment.environment": DEPLOYMENT_ENV,
        }
    )
    exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")

    existing = trace.get_tracer_provider()
    if isinstance(existing, TracerProvider):
        provider = existing
    else:
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

    provider.add_span_processor(BatchSpanProcessor(exporter))
    logger.info("OTel tracing initialized: endpoint=%s", endpoint)


def get_tracer(name: str):
    if _OTEL_AVAILABLE:
        return trace.get_tracer(name, SERVICE_VERSION)
    return None


def traced_node(tracer_name: str, span_name: str) -> Callable:
    if not _OTEL_AVAILABLE:
        def noop(fn: Callable) -> Callable:
            return fn
        return noop

    _tracer = get_tracer(tracer_name)

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attrs = {"service": SERVICE_NAME, "node": span_name}
            with _tracer.start_as_current_span(span_name, attributes=attrs):
                return await fn(*args, **kwargs)
        return wrapper
    return decorator
