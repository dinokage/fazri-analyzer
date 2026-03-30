"""
FastAPI application entry point.

Import order matters:
  app.config is imported first — it sets TF_USE_LEGACY_KERAS=1 at module
  level, which must happen before TensorFlow is imported anywhere.
  DeepFace is only imported inside the lifespan function to guarantee
  config.py has already run.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings  # sets TF env var at import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

if settings.sentry_enabled and settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )
    logger.info("Sentry initialized for environment: %s", settings.sentry_environment)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Preloading DeepFace models — may take up to 30 s on first run "
        "(weights download ~230 MB)..."
    )
    from deepface import DeepFace  # deferred so TF env var is already set

    DeepFace.build_model(settings.model_name, task="facial_recognition")
    logger.info("  %s (facial_recognition) ready", settings.model_name)

    DeepFace.build_model(settings.detector_backend, task="face_detector")
    logger.info("  %s (face_detector) ready", settings.detector_backend)

    logger.info("All models loaded. Accepting requests.")
    logger.info(
        "Active settings: model=%s detector=%s normalization=%s l2_normalize=%s",
        settings.model_name, settings.detector_backend,
        settings.normalization, settings.l2_normalize,
    )
    yield
    # No explicit teardown needed for DeepFace


def create_app() -> FastAPI:
    app = FastAPI(
        title="DeepFace Server",
        description=(
            "Face detection and recognition API powered by "
            "DeepFace + Buffalo_L + retinaface + pgvector"
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.routes import router
    app.include_router(router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level="info",
    )
