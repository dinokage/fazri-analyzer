from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Shared sub-models ────────────────────────────────────────────────────────

class FacialArea(BaseModel):
    x: int
    y: int
    w: int
    h: int
    left_eye: Optional[tuple[int, int]] = None
    right_eye: Optional[tuple[int, int]] = None


# ── /detect ──────────────────────────────────────────────────────────────────

class DetectRequest(BaseModel):
    image: str = Field(..., description="Base64-encoded image (raw or data-URI)")
    enforce_detection: bool = True


class DetectedFace(BaseModel):
    facial_area: FacialArea
    confidence: float
    face_base64: str  # PNG crop, base64-encoded


class DetectResponse(BaseModel):
    faces_detected: int
    faces: list[DetectedFace]


# ── /represent ───────────────────────────────────────────────────────────────

class RepresentRequest(BaseModel):
    image: str = Field(..., description="Base64-encoded image (raw or data-URI)")
    enforce_detection: bool = True


class FaceEmbedding(BaseModel):
    embedding: list[float]  # 512-dim for Buffalo_L
    facial_area: FacialArea
    face_confidence: float


class RepresentResponse(BaseModel):
    model_name: str
    embeddings: list[FaceEmbedding]


# ── /register ────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    image: str = Field(..., description="Base64-encoded image (raw or data-URI)")
    img_name: str = Field(..., description="Identity label stored in the DB")
    enforce_detection: bool = True


class RegisterResponse(BaseModel):
    inserted: int
    img_name: str


# ── /search ──────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    image: str = Field(..., description="Base64-encoded image (raw or data-URI)")
    enforce_detection: bool = True
    search_method: str = "exact"  # "exact" | "ann"
    similarity_search: bool = False
    k: Optional[int] = None


class SearchMatch(BaseModel):
    id: Optional[Any] = None
    img_name: Optional[str] = None
    distance: Optional[float] = None
    threshold: Optional[float] = None
    confidence: Optional[float] = None
    distance_metric: Optional[str] = None
    source_x: Optional[int] = None
    source_y: Optional[int] = None
    source_w: Optional[int] = None
    source_h: Optional[int] = None
    target_x: Optional[int] = None
    target_y: Optional[int] = None
    target_w: Optional[int] = None
    target_h: Optional[int] = None


class SearchFaceResult(BaseModel):
    """Matches for one detected face in the query image."""
    matches: list[SearchMatch]


class SearchResponse(BaseModel):
    results: list[SearchFaceResult]  # one entry per detected face


# ── /build-index ─────────────────────────────────────────────────────────────

class BuildIndexResponse(BaseModel):
    status: str
    message: str


# ── /health ──────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    model_name: str
    detector_backend: str
    database: str


# ── /stream/* ─────────────────────────────────────────────────────────────────

class StreamStartRequest(BaseModel):
    rtsp_url: str
    interval_seconds: float = 2.0
    webhook_url: str
    stream_id: Optional[str] = None


class StreamStartResponse(BaseModel):
    stream_id: str
    status: str
    rtsp_url: str
    interval_seconds: float
    webhook_url: str


class StreamInfo(BaseModel):
    stream_id: str
    rtsp_url: str
    status: str  # "running" | "stopped" | "error"
    interval_seconds: float
    webhook_url: str
    frames_processed: int
    started_at: Optional[str]
    last_error: Optional[str]


class StreamStatusResponse(BaseModel):
    streams: list[StreamInfo]


class StreamStopResponse(BaseModel):
    stream_id: str
    status: str
