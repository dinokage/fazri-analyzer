"""
SQLAlchemy model for camera stream configuration.
Stores RTSP camera stream registrations, their zone mappings, and per-camera
alert behaviour settings managed at runtime by admins.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
import uuid

from database.connection import Base


# ============================================================================
# ENUMS
# ============================================================================


class CameraStreamStatus(str, enum.Enum):
    """Lifecycle status of a camera stream"""
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"


# ============================================================================
# MODEL
# ============================================================================


class CameraStream(Base):
    """
    Represents a registered RTSP camera stream.

    Each row maps one physical camera to a campus zone.  The DeepFace server
    is told to monitor the camera's RTSP URL and to POST face-match events to
    fazri-analyzer's /api/v1/deepface/webhook endpoint.

    alert_on_unknown_face controls per-camera behaviour when a face is detected
    that has no matching entity in the DeepFace database (e.g. enable for
    restricted labs, disable for public areas).
    """

    __tablename__ = "camera_streams"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # Unique human-readable label used as stream identifier in DeepFace
    # (e.g. "cam-01", "lab-entrance-north")
    stream_id = Column(String(100), unique=True, nullable=False, index=True)

    # Full RTSP URL of the camera feed
    rtsp_url = Column(Text, nullable=False)

    # Campus zone this camera covers — matches Neo4j Zone.zone_id
    zone_id = Column(String(100), nullable=False, index=True)

    # Optional human-readable location context
    building = Column(String(200), nullable=True)
    floor = Column(String(50), nullable=True)

    # When True, an unknown face detected by this camera creates a CRITICAL alert.
    # When False, the detection is logged in Neo4j but no alert is raised.
    alert_on_unknown_face = Column(Boolean, default=True, nullable=False)

    # Current lifecycle status
    status = Column(
        Enum(CameraStreamStatus, name="camera_stream_status"),
        default=CameraStreamStatus.STOPPED,
        nullable=False,
    )

    # The stream_id value returned by DeepFace server on POST /stream/start
    # (may differ from our stream_id label if DeepFace assigns its own IDs)
    deepface_stream_id = Column(String(200), nullable=True)

    # entity_id of the admin who registered this stream
    created_by = Column(String(200), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Timestamp of the most recent face-match event received from this stream
    last_event_at = Column(DateTime, nullable=True)

    # Stores the last error message when status == ERROR
    error_message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CameraStream id={self.id} stream_id={self.stream_id!r} "
            f"zone={self.zone_id!r} status={self.status}>"
        )
