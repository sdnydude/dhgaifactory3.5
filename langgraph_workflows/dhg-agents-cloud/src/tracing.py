"""
DHG AI Factory - OpenTelemetry Tracing
=======================================
Configures OTel TracerProvider to export spans to Grafana Tempo
via OTLP gRPC (dhg-tempo:4317).

Dual-export strategy: LangSmith (@traceable) for LLM-specific traces,
OpenTelemetry for infrastructure-level distributed tracing in Tempo.

Gracefully degrades when OTel packages are not installed (e.g. LangGraph Cloud).

Author: Digital Harmony Group
Version: 1.1.0
"""

import os
import functools
import logging
from typing import Callable, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to import OTel — gracefully degrade if not available
# ---------------------------------------------------------------------------

_OTEL_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    _OTEL_AVAILABLE = True
except ImportError:
    trace = None
    logger.info("OpenTelemetry not available — tracing disabled (expected in Cloud)")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SERVICE_NAME = "dhg-langgraph-agents"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENVIRONMENT", "production")

TEMPO_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://localhost:4317",
)

# ---------------------------------------------------------------------------
# Provider setup (runs once on first import, only if OTel is available)
# ---------------------------------------------------------------------------

if _OTEL_AVAILABLE:
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

def get_tracer(name: str):
    """Return a tracer scoped to the given module or agent name."""
    if _OTEL_AVAILABLE:
        return trace.get_tracer(name, SERVICE_VERSION)
    return None


def traced_node(
    tracer_name: str,
    span_name: str,
    attributes: Optional[Dict[str, str]] = None,
) -> Callable:
    """Decorator that wraps an async LangGraph node function with an OTel span.

    When OTel is not available, acts as a no-op passthrough decorator.
    """
    if not _OTEL_AVAILABLE:
        def noop_decorator(fn: Callable) -> Callable:
            return fn
        return noop_decorator

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
