# services/medkb/src/medkb/main.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from medkb.config import Settings
from medkb.endpoints.corpora import router as corpora_router
from medkb.endpoints.health import router as health_router
from medkb.endpoints.query import router as query_router
import medkb.metrics  # noqa: F401 — registers all Prometheus metrics with the default registry
from medkb.tracing import init_tracing

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_tracing(settings.otel_endpoint)
    logger.info("medkb starting: port=%d", settings.api_port)
    yield
    logger.info("medkb shutting down")


app = FastAPI(
    title="dhg-medkb",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(corpora_router)
app.include_router(query_router)


if __name__ == "__main__":
    uvicorn.run(
        "medkb.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        log_level="info",
    )
