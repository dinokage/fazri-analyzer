"""
FastAPI application entry point for the face recognition service.

Uses InsightFace (buffalo_l) directly for detection + recognition,
and pgvector for embedding storage/search. No DeepFace or TensorFlow.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

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
    logger.info("Loading InsightFace buffalo_l model pack (SCRFD + ArcFace)...")
    from app.face_engine import load_engine
    load_engine()

    logger.info("Ensuring pgvector schema (face_embeddings table + HNSW index)...")
    from app.pgvector_service import get_pgvector_service
    pgv = get_pgvector_service()
    pgv.ensure_schema()
    count = pgv.count_all()
    logger.info("pgvector ready: %d embeddings in database", count)

    logger.info("All models loaded. Accepting requests.")
    logger.info(
        "Active settings: det_size=%d cosine_threshold=%.2f face_track_sim=%.2f",
        settings.det_size, settings.cosine_threshold, settings.face_track_similarity,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Face Recognition Server",
        description="Face detection and recognition powered by InsightFace (buffalo_l) + pgvector",
        version="0.2.0",
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
