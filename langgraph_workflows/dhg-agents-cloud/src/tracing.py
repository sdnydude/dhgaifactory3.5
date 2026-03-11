"""
DHG AI Factory - OpenTelemetry Tracing
=======================================
Configures OTel TracerProvider to export spans to Grafana Tempo
via OTLP gRPC (dhg-tempo:4317).

Dual-export strategy: LangSmith (@traceable) for LLM-specific traces,
OpenTelemetry for infrastructure-level distributed tracing in Tempo.

Auto-initializes on import. Use get_tracer(name) to obtain a tracer.

Author: Digital Harmony Group
Version: 1.0.0
"""

import os
import functools
import logging
from typing import Callable, Dict, Any, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SERVICE_NAME = "dhg-langgraph-agents"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENVIRONMENT", "production")

TEMPO_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://dhg-tempo:4317",
)

# ---------------------------------------------------------------------------
# Provider setup (runs once on first import)
# ---------------------------------------------------------------------------

_resource = Resource.create(
    {
        "service.name": SERVICE_NAME,
        "service.version": SERVICE_VERSION,
        "deployment.environment": DEPLOYMENT_ENV,
    }
)

_provider = TracerProvider(resource=_resource)

_exporter = OTLPSpanExporter(
    endpoint=TEMPO_ENDPOINT,
    insecure=True,
)

_provider.add_span_processor(BatchSpanProcessor(_exporter))

trace.set_tracer_provider(_provider)

logger.info(
    "OpenTelemetry initialized: service=%s endpoint=%s env=%s",
    SERVICE_NAME,
    TEMPO_ENDPOINT,
    DEPLOYMENT_ENV,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_tracer(name: str) -> trace.Tracer:
    """Return a tracer scoped to the given module or agent name.

    Example::

        from tracing import get_tracer
        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("my_operation"):
            ...
    """
    return trace.get_tracer(name, SERVICE_VERSION)


def traced_node(
    tracer_name: str,
    span_name: str,
    attributes: Optional[Dict[str, str]] = None,
) -> Callable:
    """Decorator that wraps an async LangGraph node function with an OTel span.

    Designed to stack with ``@traceable`` for dual-export (LangSmith + Tempo).
    Place **below** ``@traceable`` so the OTel span is the inner wrapper::

        @traceable(name="my_node", run_type="chain")
        @traced_node("my_agent", "my_node")
        async def my_node(state: MyState) -> dict:
            ...

    The decorator automatically sets ``agent`` and ``node`` span attributes
    and records exceptions on the span without swallowing them.
    """
    _tracer = get_tracer(tracer_name)

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            merged_attrs = {"agent": tracer_name, "node": span_name}
            if attributes:
                merged_attrs.update(attributes)
            with _tracer.start_as_current_span(span_name, attributes=merged_attrs):
                return await fn(*args, **kwargs)
        return wrapper
    return decorator
