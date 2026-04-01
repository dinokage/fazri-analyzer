from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.config import settings
from app.schemas import (
    BuildIndexResponse,
    DetectRequest,
    DetectResponse,
    DetectedFace,
    FaceEmbedding,
    FacialArea,
    HealthResponse,
    RegisterRequest,
    RegisterResponse,
    RepresentRequest,
    RepresentResponse,
    SearchFaceResult,
    SearchMatch,
    SearchRequest,
    SearchResponse,
    StreamInfo,
    StreamStartRequest,
    StreamStartResponse,
    StreamStatusResponse,
    StreamStopResponse,
)
from app.utils import df_to_search_matches, load_image_input, ndarray_to_base64_png

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Error helpers ─────────────────────────────────────────────────────────────

def _422(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _500(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


# ── Input resolution ──────────────────────────────────────────────────────────

async def _resolve(request: Request, file: Optional[UploadFile]) -> tuple[str, dict]:
    """
    Parse image input and any JSON fields from either multipart or JSON body.
    Returns (data_uri, extra_fields_dict).
    """
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        b64 = None
        extra = {k: v for k, v in form.items() if k != "file"}
    else:
        try:
            payload = await request.json()
        except Exception:
            raise _422("Invalid JSON body")
        b64 = payload.pop("image", None)
        extra = payload
        file = None

    if file is None and b64 is None:
        raise _422("Provide either a multipart 'file' field or a JSON 'image' field (base64).")

    data_uri = await load_image_input(file, b64)
    return data_uri, extra


def _bool(val, default: bool = True) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() not in ("false", "0", "no")
    return default


# ── GET /health ───────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    db_host = settings.deepface_postgres_uri.split("@")[-1]
    return HealthResponse(
        status="ok",
        model_name=settings.model_name,
        detector_backend=settings.detector_backend,
        database=db_host,
    )


# ── POST /detect ──────────────────────────────────────────────────────────────

@router.post("/detect", response_model=DetectResponse, tags=["detection"])
async def detect(request: Request, file: Optional[UploadFile] = File(default=None)):
    """Detect all faces in an image; return bounding boxes and base64 PNG crops."""
    from deepface import DeepFace
    from deepface.modules.exceptions import FaceNotDetected, ImgNotFound

    data_uri, extra = await _resolve(request, file)
    enforce = _bool(extra.get("enforce_detection", True))

    try:
        faces_raw = DeepFace.extract_faces(
            img_path=data_uri,
            detector_backend=settings.detector_backend,
            enforce_detection=enforce,
            align=True,
            color_face="rgb",
            normalize_face=True,
        )
    except FaceNotDetected as exc:
        raise _422(str(exc)) from exc
    except ImgNotFound as exc:
        raise _422(str(exc)) from exc
    except ValueError as exc:
        raise _422(str(exc)) from exc

    faces_out = []
    for f in faces_raw:
        area = f["facial_area"]
        faces_out.append(
            DetectedFace(
                facial_area=FacialArea(
                    x=area["x"],
                    y=area["y"],
                    w=area["w"],
                    h=area["h"],
                    left_eye=area.get("left_eye"),
                    right_eye=area.get("right_eye"),
                ),
                confidence=float(f["confidence"]),
                face_base64=ndarray_to_base64_png(f["face"]),
            )
        )

    return DetectResponse(faces_detected=len(faces_out), faces=faces_out)


# ── POST /represent ───────────────────────────────────────────────────────────

@router.post("/represent", response_model=RepresentResponse, tags=["recognition"])
async def represent(request: Request, file: Optional[UploadFile] = File(default=None)):
    """Return 512-dim Buffalo_L embeddings for every face in the image."""
    from deepface import DeepFace
    from deepface.modules.exceptions import FaceNotDetected, ImgNotFound

    data_uri, extra = await _resolve(request, file)
    enforce = _bool(extra.get("enforce_detection", True))

    try:
        reps = DeepFace.represent(
            img_path=data_uri,
            model_name=settings.model_name,
            detector_backend=settings.detector_backend,
            enforce_detection=enforce,
            align=True,
            normalization=settings.normalization,
            l2_normalize=settings.l2_normalize,
        )
    except FaceNotDetected as exc:
        raise _422(str(exc)) from exc
    except ImgNotFound as exc:
        raise _422(str(exc)) from exc
    except ValueError as exc:
        raise _422(str(exc)) from exc

    embeddings_out = []
    for r in reps:
        area = r["facial_area"]
        embeddings_out.append(
            FaceEmbedding(
                embedding=r["embedding"],
                facial_area=FacialArea(x=area["x"], y=area["y"], w=area["w"], h=area["h"]),
                face_confidence=float(r["face_confidence"]),
            )
        )

    return RepresentResponse(model_name=settings.model_name, embeddings=embeddings_out)


# ── POST /register ────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, tags=["database"])
async def register(request: Request, file: Optional[UploadFile] = File(default=None)):
    """Register a face into the pgvector database with an identity label."""
    from deepface import DeepFace
    from deepface.modules.exceptions import (
        DimensionMismatchError,
        FaceNotDetected,
        ImgNotFound,
    )

    data_uri, extra = await _resolve(request, file)
    enforce = _bool(extra.get("enforce_detection", True))
    name = extra.get("img_name")

    if not name:
        raise _422("'img_name' is required for registration.")

    try:
        result = DeepFace.register(
            img=data_uri,
            img_name=name,
            model_name=settings.model_name,
            detector_backend=settings.detector_backend,
            enforce_detection=enforce,
            align=True,
            expand_percentage=settings.expand_percentage,
            normalization=settings.normalization,
            l2_normalize=settings.l2_normalize,
            database_type="postgres",
            connection_details=settings.connection_details,
        )
    except FaceNotDetected as exc:
        raise _422(str(exc)) from exc
    except ImgNotFound as exc:
        raise _422(str(exc)) from exc
    except DimensionMismatchError as exc:
        raise _500(f"Embedding dimension mismatch: {exc}") from exc
    except ValueError as exc:
        raise _422(str(exc)) from exc

    return RegisterResponse(inserted=result["inserted"], img_name=name)


# ── POST /search ──────────────────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse, tags=["database"])
async def search(request: Request, file: Optional[UploadFile] = File(default=None)):
    """Search the pgvector database for faces matching the query image."""
    from deepface import DeepFace
    from deepface.modules.exceptions import EmptyDatasource, FaceNotDetected, ImgNotFound

    data_uri, extra = await _resolve(request, file)
    enforce = _bool(extra.get("enforce_detection", True))
    search_method = extra.get("search_method", "exact")
    similarity_search = _bool(extra.get("similarity_search", False), default=False)
    k_raw = extra.get("k")
    k = int(k_raw) if k_raw is not None else None

    try:
        dfs = DeepFace.search(
            img=data_uri,
            model_name=settings.model_name,
            detector_backend=settings.detector_backend,
            distance_metric=settings.distance_metric,
            enforce_detection=enforce,
            align=True,
            expand_percentage=settings.expand_percentage,
            normalization=settings.normalization,
            l2_normalize=settings.l2_normalize,
            database_type="postgres",
            connection_details=settings.connection_details,
            search_method=search_method,
            similarity_search=similarity_search,
            k=k,
        )
    except FaceNotDetected as exc:
        raise _422(str(exc)) from exc
    except ImgNotFound as exc:
        raise _422(str(exc)) from exc
    except EmptyDatasource:
        return SearchResponse(results=[])
    except ValueError as exc:
        raise _422(str(exc)) from exc

    results_out = []
    for df in dfs:
        if df.empty:
            results_out.append(SearchFaceResult(matches=[]))
        else:
            # DeepFace.search() already filters by its internal threshold (0.55 for Buffalo_L)
            # We keep results as-is so we can see actual distances for tuning
            raw_matches = df_to_search_matches(df)
            results_out.append(
                SearchFaceResult(matches=[SearchMatch(**m) for m in raw_matches])
            )

    return SearchResponse(results=results_out)


# ── POST /build-index ─────────────────────────────────────────────────────────

@router.post("/build-index", response_model=BuildIndexResponse, tags=["database"])
async def build_index():
    """Build the ANN index on the pgvector DB for fast approximate search."""
    from deepface import DeepFace
    from deepface.modules.exceptions import EmptyDatasource

    try:
        DeepFace.build_index(
            model_name=settings.model_name,
            database_type="postgres",
            connection_details=settings.connection_details,
        )
    except EmptyDatasource:
        raise _422("Cannot build index: database has no registered faces.")
    except ValueError as exc:
        raise _500(str(exc)) from exc

    return BuildIndexResponse(
        status="ok",
        message=f"ANN index built successfully for model '{settings.model_name}'.",
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
