"""
Pydantic schemas for the DeepFace Integration.
Used for request/response validation on all /api/v1/deepface endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# WEBHOOK PAYLOAD  (inbound from DeepFace server)
# ============================================================================


class FacialArea(BaseModel):
    """Bounding box of a detected face within a video frame"""
    x: int
    y: int
    w: int
    h: int


class FaceMatch(BaseModel):
    """
    A single face-recognition match result.
    img_name is the label set at registration time — in fazri-analyzer this
    equals the entity's entity_id.
    """
    img_name: str = Field(..., description="Label used at registration — maps to entity_id")
    distance: float = Field(..., description="0.0 = identical; >threshold = no match")
    confidence: float = Field(..., description="Percent confidence (0-100)")
    threshold: float = Field(..., description="Distance threshold used for this model")
    facial_area: Optional[FacialArea] = None


class WebhookPayload(BaseModel):
    """
    Payload sent by the DeepFace server to POST /api/v1/deepface/webhook
    whenever a face is matched in an RTSP stream.
    """
    stream_id: str = Field(..., description="Camera stream identifier")
    rtsp_url: str = Field(..., description="The RTSP URL that was being monitored")
    timestamp: datetime = Field(..., description="When the detection occurred")
    frames_processed: int = Field(..., ge=0)
    faces_found: int = Field(..., ge=0)
    matches: List[FaceMatch] = Field(default_factory=list)


# ============================================================================
# STREAM MANAGEMENT  (admin CRUD)
# ============================================================================


class StreamCreateRequest(BaseModel):
    """Request body for POST /api/v1/deepface/streams"""
    stream_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique label for this camera (e.g. 'cam-01')",
    )
    rtsp_url: str = Field(
        ...,
        description="Full RTSP URL of the camera (e.g. rtsp://admin:pass@192.168.1.10/stream1)",
    )
    zone_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Campus zone ID this camera covers (matches Neo4j Zone.zone_id)",
    )
    building: Optional[str] = Field(None, max_length=200)
    floor: Optional[str] = Field(None, max_length=50)
    alert_on_unknown_face: bool = Field(
        True,
        description="When True, an unrecognised face triggers a CRITICAL alert",
    )


class StreamUpdateRequest(BaseModel):
    """Request body for PATCH /api/v1/deepface/streams/{stream_id}"""
    zone_id: Optional[str] = Field(None, max_length=100)
    building: Optional[str] = Field(None, max_length=200)
    floor: Optional[str] = Field(None, max_length=50)
    alert_on_unknown_face: Optional[bool] = None


class StreamResponse(BaseModel):
    """Response schema for a single camera stream"""
    id: UUID
    stream_id: str
    rtsp_url: str
    zone_id: str
    building: Optional[str]
    floor: Optional[str]
    alert_on_unknown_face: bool
    status: str
    deepface_stream_id: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_event_at: Optional[datetime]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class StreamListResponse(BaseModel):
    """Paginated list of camera streams"""
    streams: List[StreamResponse]
    total: int


# ============================================================================
# FACE REGISTRATION
# ============================================================================


class FaceRegistrationResponse(BaseModel):
    """Response for POST /api/v1/deepface/entities/{entity_id}/register"""
    entity_id: str
    registered: bool
    message: str
    # Remind the caller to update the user record via the auth service
    note: str = (
        "Update the user's face_id field via the auth service API "
        "using entity_id as the new face_id value."
    )


# ============================================================================
# FACE SEARCH
# ============================================================================


class FaceSearchResult(BaseModel):
    """A single result from POST /api/v1/deepface/search, enriched with entity data"""
    img_name: str = Field(..., description="Registered label (= entity_id)")
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    entity_role: Optional[str] = None
    entity_department: Optional[str] = None
    distance: float
    confidence: float
    threshold: float


class FaceSearchResponse(BaseModel):
    """Response for POST /api/v1/deepface/search"""
    results: List[FaceSearchResult]
    query_time_ms: Optional[float] = None


# ============================================================================
# WEBHOOK RESPONSE
# ============================================================================


class WebhookProcessedResponse(BaseModel):
    """Response returned after processing a webhook payload"""
    status: str = "ok"
    processed: int = Field(..., description="Number of face matches processed")
    alerts_created: int = Field(0, description="Number of alerts triggered")
