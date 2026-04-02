"""
Canonical internal sensor event schema for FAZRI.

Every data source — Hikvision RFID readers, Aruba WiFi access points, and
DeepFace camera streams — MUST normalize raw hardware events into a
``SensorEvent`` before they enter the entity resolution pipeline.

This is the single contract between ingestion and resolution.  Connectors
translate; everything downstream consumes ``SensorEvent``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SensorType(str, Enum):
    """Physical or logical source of the event."""

    RFID = "RFID"
    WIFI = "WIFI"
    CAMERA = "CAMERA"
    BIOMETRIC = "BIOMETRIC"
    MANUAL = "MANUAL"


class EventType(str, Enum):
    """Semantic meaning of the event."""

    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_DENIED = "ACCESS_DENIED"
    DEVICE_ASSOCIATED = "DEVICE_ASSOCIATED"
    DEVICE_DISASSOCIATED = "DEVICE_DISASSOCIATED"
    FACE_RECOGNIZED = "FACE_RECOGNIZED"
    FACE_UNKNOWN = "FACE_UNKNOWN"
    ENTRY = "ENTRY"
    EXIT = "EXIT"


# ---------------------------------------------------------------------------
# Core event model
# ---------------------------------------------------------------------------


class SensorEvent(BaseModel):
    """
    Unified internal representation of a sensor event.

    Fields
    ------
    event_id
        Auto-generated UUID string.  Stable identifier used for deduplication
        and audit.
    sensor_type
        The category of sensor that produced this event.
    event_type
        The semantic action that occurred.
    timestamp
        UTC datetime of the event.  **Must be timezone-aware.**
    zone_id
        References the campus zone where the event occurred.  Must match a
        Zone node in the graph database.
    raw_identifier
        The hardware-level identifier as received from the device, e.g. a
        card number, a MAC address, or a face embedding label.
    identifier_type
        Describes the kind of ``raw_identifier`` so the entity resolver can
        apply the correct lookup, e.g. ``"card_id"``, ``"mac_address"``,
        ``"face_id"``, ``"entity_id"``.
    resolved_entity_id
        Filled by ``EntityResolutionService`` after ingestion.  ``None`` means
        the identifier could not be mapped to a known entity.
    confidence
        Resolution confidence in [0.0, 1.0].  Use ``1.0`` for deterministic
        sources (RFID).  Probabilistic sources (face recognition) should
        supply the model's output score.
    source_device_id
        Optional identifier of the physical device, e.g. NVR serial number,
        AP hostname.
    building / floor
        Optional location refinement within a zone.
    raw_payload
        Full original event dict kept for debugging and future re-processing.
    metadata
        Connector-specific extension fields.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Auto-generated UUID for this event",
    )
    sensor_type: SensorType
    event_type: EventType
    timestamp: datetime = Field(
        ...,
        description="UTC timestamp — must be timezone-aware",
    )
    zone_id: str = Field(..., description="Zone where the event occurred")
    raw_identifier: str = Field(
        ...,
        description="Hardware-level ID (card number, MAC, face label)",
    )
    identifier_type: str = Field(
        ...,
        description='Kind of identifier, e.g. "card_id", "mac_address", "face_id"',
    )
    resolved_entity_id: Optional[str] = Field(
        None,
        description="Filled by EntityResolutionService after ingestion",
    )
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Resolution confidence: 1.0 for deterministic, <1.0 for probabilistic",
    )
    source_device_id: Optional[str] = Field(
        None,
        description="NVR serial, AP name, or other device identifier",
    )
    building: Optional[str] = None
    floor: Optional[str] = None
    raw_payload: Optional[dict] = Field(
        None,
        description="Full original event dict for debugging",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Connector-specific extension fields",
    )

    # ------------------------------------------------------------------
    # Factory stubs — implemented in Week 2 connectors
    # ------------------------------------------------------------------

    @classmethod
    def from_hikvision_access(cls, raw: dict) -> "SensorEvent":
        """
        Normalize a raw Hikvision ISAPI AcsEvent dict into a SensorEvent.

        Implemented in ``backend/connectors/hikvision_client.py`` (Week 2).
        """
        raise NotImplementedError(
            "from_hikvision_access is not yet implemented. "
            "Implement it in backend/connectors/hikvision_client.py."
        )

    @classmethod
    def from_aruba_association(cls, raw: dict) -> "SensorEvent":
        """
        Normalize a raw Aruba AOS8 client association dict into a SensorEvent.

        Implemented in ``backend/connectors/aruba_client.py`` (Week 2).
        """
        raise NotImplementedError(
            "from_aruba_association is not yet implemented. "
            "Implement it in backend/connectors/aruba_client.py."
        )

    @classmethod
    def from_deepface_match(cls, raw: dict) -> "SensorEvent":
        """
        Normalize a raw DeepFace webhook match dict into a SensorEvent.

        Implemented in ``backend/routes/deepface_routes.py`` (Week 2, Task 2.3).
        """
        raise NotImplementedError(
            "from_deepface_match is not yet implemented. "
            "Implement it in backend/routes/deepface_routes.py."
        )


# ---------------------------------------------------------------------------
# Resolved event model
# ---------------------------------------------------------------------------


class ResolvedEvent(SensorEvent):
    """
    A ``SensorEvent`` that has been successfully matched to a known entity.

    All fields from ``SensorEvent`` are inherited.  The differences are:

    * ``resolved_entity_id`` is **required** (not Optional).
    * Three entity profile fields are added for convenience — they are
      denormalized copies that avoid a second DB lookup in the alert pipeline.
    """

    resolved_entity_id: str = Field(
        ...,
        description="Canonical FAZRI entity ID — required on a resolved event",
    )
    entity_name: Optional[str] = Field(
        None,
        description="Display name from entity_profiles",
    )
    entity_role: Optional[str] = Field(
        None,
        description='Role from entity_profiles, e.g. "STUDENT", "STAFF"',
    )
    entity_department: Optional[str] = Field(
        None,
        description="Department from entity_profiles",
    )
