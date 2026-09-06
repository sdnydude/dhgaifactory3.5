"""
DHG AI FACTORY - AGENT TRACING (Langfuse over OpenTelemetry)
============================================================
Tracing substrate for agents built on Pydantic AI. Replaces the retired
LangSmith `@traceable` decorator: Pydantic AI emits OpenTelemetry spans once
`Agent.instrument_all()` is called, and those spans are shipped to the
self-hosted Langfuse v3 OTLP ingest endpoint.

DOCUMENTED NO-OP
----------------
Tracing is opt-in. When `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are not
both present in the environment, `configure_tracing()`:

  * sets no OTEL_* environment variables,
  * imports no OpenTelemetry SDK module,
  * installs no exporter and starts no background export thread,
  * never calls `Agent.instrument_all()`, and
  * returns False.

The agent then runs completely untraced and makes no network call to Langfuse.
This is the expected state on a developer laptop and in CI.

CREDENTIALS
-----------
`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` are the runtime names. In Doppler
the AI Factory keys are stored as `LANGFUSE_AIFACTORY_PUBLIC_KEY` and
`LANGFUSE_AIFACTORY_SECRET_KEY`; map them onto the runtime names when injecting
(see README.md).
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Dict, Optional, Tuple

LOGGER = logging.getLogger(__name__)

# Self-hosted Langfuse v3 OTLP ingest endpoint (dh40801). The OTLP HTTP exporter
# appends `/v1/traces` to this base URL.
DEFAULT_OTLP_ENDPOINT = "http://10.0.0.179:3000/api/public/otel"

PUBLIC_KEY_ENV = "LANGFUSE_PUBLIC_KEY"
SECRET_KEY_ENV = "LANGFUSE_SECRET_KEY"
ENDPOINT_ENV = "LANGFUSE_OTLP_ENDPOINT"


def langfuse_credentials() -> Optional[Tuple[str, str]]:
    """Return (public_key, secret_key) when both are set and non-empty, else None."""
    public_key = os.getenv(PUBLIC_KEY_ENV, "").strip()
    secret_key = os.getenv(SECRET_KEY_ENV, "").strip()
    if public_key and secret_key:
        return public_key, secret_key
    return None


def tracing_enabled() -> bool:
    """True when Langfuse credentials are present in the environment."""
    return langfuse_credentials() is not None


def basic_auth_header(public_key: str, secret_key: str) -> str:
    """Build the OTLP `Authorization` header value Langfuse expects.

    Langfuse authenticates OTLP ingest with HTTP Basic auth over
    `<public_key>:<secret_key>`, in the `key=value` form that
    `OTEL_EXPORTER_OTLP_HEADERS` parses.
    """
    token = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("ascii")
    return f"Authorization=Basic {token}"


def build_otlp_env(
    public_key: str,
    secret_key: str,
    endpoint: Optional[str] = None,
) -> Dict[str, str]:
    """Build the OTLP exporter environment for Langfuse ingest."""
    resolved = endpoint or os.getenv(ENDPOINT_ENV) or DEFAULT_OTLP_ENDPOINT
    return {
        "OTEL_EXPORTER_OTLP_ENDPOINT": resolved,
        "OTEL_EXPORTER_OTLP_HEADERS": basic_auth_header(public_key, secret_key),
        "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
    }


def configure_tracing(service_name: str) -> bool:
    """Wire Pydantic AI spans to Langfuse. Returns True when tracing is live.

    Safe to call at import time, and a no-op without credentials (see module
    docstring).
    """
    credentials = langfuse_credentials()
    if credentials is None:
        LOGGER.info(
            "Langfuse keys absent (%s/%s) - tracing disabled, agent runs untraced",
            PUBLIC_KEY_ENV,
            SECRET_KEY_ENV,
        )
        return False

    os.environ.update(build_otlp_env(*credentials))

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from pydantic_ai import Agent

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    Agent.instrument_all()

    LOGGER.info(
        "Langfuse tracing enabled for %s -> %s",
        service_name,
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"],
    )
    return True
