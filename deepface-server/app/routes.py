from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.config import settings
from app.schemas import (
    BuildIndexResponse,
    DetectResponse,
    DetectedFace,
    FaceEmbedding,
    FacialArea,
    HealthResponse,
    RegisterResponse,
    RepresentResponse,
    SearchFaceResult,
    SearchMatch,
    SearchResponse,
    StreamInfo,
    StreamStartRequest,
    StreamStartResponse,
    StreamStatusResponse,
    StreamStopResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Error helpers ─────────────────────────────────────────────────────────────

def _422(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _500(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


# ── Input resolution ──────────────────────────────────────────────────────────

async def _resolve_image(request: Request, file: Optional[UploadFile]) -> tuple[np.ndarray, dict]:
    """
    Parse image input from multipart or JSON body.
    Returns (BGR numpy array, extra_fields_dict).
    """
    import base64

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        extra = {k: v for k, v in form.items() if k != "file"}
        if file is None:
            raise _422("Provide a multipart 'file' field.")
        image_bytes = await file.read()
    else:
        try:
            payload = await request.json()
        except Exception:
            raise _422("Invalid JSON body")
        b64 = payload.pop("image", None)
        extra = payload
        file = None
        if not b64:
            raise _422("Provide a JSON 'image' field (base64).")
        # Strip data-URI prefix if present
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        image_bytes = base64.b64decode(b64)

    # Decode to BGR numpy array (no JPEG re-encoding)
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise _422("Could not decode the image.")
    return frame, extra


def _bool(val, default: bool = True) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() not in ("false", "0", "no")
    return default


# ── GET /health ───────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    from app.pgvector_service import get_pgvector_service
    pgv = get_pgvector_service()
    count = pgv.count_all()
    db_host = settings.deepface_postgres_uri.split("@")[-1]
    return HealthResponse(
        status="ok",
        model_name="buffalo_l (InsightFace)",
        detector_backend="SCRFD (bundled)",
        database=f"{db_host} ({count} embeddings)",
    )


# ── POST /detect ──────────────────────────────────────────────────────────────

@router.post("/detect", response_model=DetectResponse, tags=["detection"])
async def detect(request: Request, file: Optional[UploadFile] = File(default=None)):
    """Detect all faces in an image; return bounding boxes."""
    from app.face_engine import detect_and_embed

    frame, _extra = await _resolve_image(request, file)
    faces = detect_and_embed(frame)

    faces_out = []
    for f in faces:
        x1, y1, x2, y2 = f["bbox"]
        faces_out.append(
            DetectedFace(
                facial_area=FacialArea(x=x1, y=y1, w=x2 - x1, h=y2 - y1),
                confidence=f["det_score"],
                face_base64="",  # not needed for new pipeline
            )
        )

    return DetectResponse(faces_detected=len(faces_out), faces=faces_out)


# ── POST /represent ───────────────────────────────────────────────────────────

@router.post("/represent", response_model=RepresentResponse, tags=["recognition"])
async def represent(request: Request, file: Optional[UploadFile] = File(default=None)):
    """Return 512-dim embeddings for every face in the image."""
    from app.face_engine import detect_and_embed

    frame, _extra = await _resolve_image(request, file)
    faces = detect_and_embed(frame)

    if not faces:
        raise _422("No face detected in the image.")

    embeddings_out = []
    for f in faces:
        x1, y1, x2, y2 = f["bbox"]
        embeddings_out.append(
            FaceEmbedding(
                embedding=f["embedding"].tolist(),
                facial_area=FacialArea(x=x1, y=y1, w=x2 - x1, h=y2 - y1),
                face_confidence=f["det_score"],
            )
        )

    return RepresentResponse(model_name="buffalo_l", embeddings=embeddings_out)


# ── POST /register ────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, tags=["database"])
async def register(request: Request, file: Optional[UploadFile] = File(default=None)):
    """Register a face into the pgvector database with an identity label."""
    from app.face_engine import embed_single
    from app.pgvector_service import get_pgvector_service

    frame, extra = await _resolve_image(request, file)
    name = extra.get("img_name")
    if not name:
        raise _422("'img_name' is required for registration.")

    face = embed_single(frame)
    if face is None:
        raise _422("No face detected in the uploaded image.")

    pgv = get_pgvector_service()
    row_id = pgv.register(
        identity_name=str(name),
        embedding=face["embedding"],
        det_score=face["det_score"],
    )
    logger.info("Registered face for '%s' (row_id=%d, det_score=%.3f)", name, row_id, face["det_score"])

    return RegisterResponse(inserted=1, img_name=str(name))


# ── POST /search ──────────────────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse, tags=["database"])
async def search(request: Request, file: Optional[UploadFile] = File(default=None)):
    """Search the pgvector database for faces matching the query image."""
    from app.face_engine import detect_and_embed
    from app.pgvector_service import get_pgvector_service

    frame, extra = await _resolve_image(request, file)
    threshold = float(extra.get("threshold", settings.cosine_threshold))
    k = int(extra.get("k", 5))

    faces = detect_and_embed(frame)
    if not faces:
        raise _422("No face detected in the image.")

    pgv = get_pgvector_service()
    results_out = []

    for face in faces:
        matches = pgv.search(face["embedding"], threshold=threshold, limit=k)
        x1, y1, x2, y2 = face["bbox"]
        results_out.append(
            SearchFaceResult(
                matches=[
                    SearchMatch(
                        img_name=m["identity_name"],
                        distance=m["distance"],
                        threshold=threshold,
                        confidence=face["det_score"] * 100,
                        distance_metric="cosine",
                        target_x=x1,
                        target_y=y1,
                        target_w=x2 - x1,
                        target_h=y2 - y1,
                    )
                    for m in matches
                ]
            )
        )

    return SearchResponse(results=results_out)


# ── POST /build-index ─────────────────────────────────────────────────────────

@router.post("/build-index", response_model=BuildIndexResponse, tags=["database"])
async def build_index():
    """HNSW index is created automatically on table creation. This is a no-op."""
    return BuildIndexResponse(
        status="ok",
        message="HNSW index is created automatically with the face_embeddings table.",
    )


# ── POST /stream/start ────────────────────────────────────────────────────────

@router.post("/stream/start", response_model=StreamStartResponse, tags=["streams"])
async def stream_start(body: StreamStartRequest):
    """Start processing an RTSP stream; results posted to webhook_url."""
    from app.stream import start_stream

    try:
        processor = await start_stream(
            rtsp_url=body.rtsp_url,
            interval_seconds=body.interval_seconds,
            webhook_url=body.webhook_url,
            stream_id=body.stream_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return StreamStartResponse(
        stream_id=processor.stream_id,
        status=processor.status,
        rtsp_url=processor.rtsp_url,
        interval_seconds=processor.interval_seconds,
        webhook_url=processor.webhook_url,
    )


# ── POST /stream/stop/{stream_id} ─────────────────────────────────────────────

@router.post("/stream/stop/{stream_id}", response_model=StreamStopResponse, tags=["streams"])
async def stream_stop(stream_id: str):
    """Stop a running RTSP stream processor."""
    from app.stream import stop_stream

    try:
        processor = await stop_stream(stream_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return StreamStopResponse(stream_id=processor.stream_id, status="stopped")


# ── GET /stream/status ────────────────────────────────────────────────────────

@router.get("/stream/status", response_model=StreamStatusResponse, tags=["streams"])
async def stream_status():
    """List all active stream processors and their current state."""
    from app.stream import get_all_streams

    streams = [
        StreamInfo(
            stream_id=p.stream_id,
            rtsp_url=p.rtsp_url,
            status=p.status,
            interval_seconds=p.interval_seconds,
            webhook_url=p.webhook_url,
            frames_processed=p.frames_processed,
            started_at=p.started_at.isoformat() if p.started_at else None,
            last_error=p.last_error,
        )
        for p in get_all_streams()
    ]
    return StreamStatusResponse(streams=streams)
