"""
Sensor events API routes.

GET /api/v1/events  — paginated sensor event feed with optional filters.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import require_staff
from auth.models import AuthenticatedUser
from database.connection import get_db
from models.db.sensor_events import SensorEventRecord
from models.db.entity_profiles import EntityProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class SensorEventResponse(BaseModel):
    event_id: str
    sensor_type: str
    event_type: str
    timestamp: datetime
    zone_id: str
    raw_identifier: str
    identifier_type: str
    resolved_entity_id: Optional[str]
    entity_name: Optional[str]
    confidence: float
    source_device_id: Optional[str]
    building: Optional[str]
    floor: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SensorEventListResponse(BaseModel):
    items: List[SensorEventResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SensorEventListResponse,
    summary="List sensor events",
    description=(
        "Returns a paginated, filtered list of sensor events from all sources "
        "(RFID, WiFi, Camera) sorted by timestamp descending."
    ),
)
async def list_events(
    # Filters
    sensor_type: Optional[str] = Query(
        None,
        description="Comma-separated sensor types: RFID,WIFI,CAMERA",
    ),
    zone_id: Optional[str] = Query(None, description="Filter by zone_id"),
    resolved: Optional[bool] = Query(
        None, description="true=resolved only, false=unresolved only, omit=all"
    ),
    since: Optional[datetime] = Query(
        None, description="Only events after this ISO 8601 timestamp"
    ),
    until: Optional[datetime] = Query(
        None, description="Only events before this ISO 8601 timestamp"
    ),
    # Pagination
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    # Auth
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> SensorEventListResponse:
    query = db.query(SensorEventRecord)

    # ── Filters ───────────────────────────────────────────────────────────────
    if sensor_type:
        types = [t.strip().upper() for t in sensor_type.split(",")]
        query = query.filter(SensorEventRecord.sensor_type.in_(types))

    if zone_id:
        query = query.filter(SensorEventRecord.zone_id == zone_id)

    if resolved is True:
        query = query.filter(SensorEventRecord.resolved_entity_id.isnot(None))
    elif resolved is False:
        query = query.filter(SensorEventRecord.resolved_entity_id.is_(None))

    if since:
        if since.tzinfo is None:
            raise HTTPException(
                status_code=400,
                detail="'since' must be timezone-aware (e.g. 2024-01-01T00:00:00Z)",
            )
        query = query.filter(SensorEventRecord.timestamp >= since)

    if until:
        if until.tzinfo is None:
            raise HTTPException(
                status_code=400,
                detail="'until' must be timezone-aware (e.g. 2024-01-01T00:00:00Z)",
            )
        query = query.filter(SensorEventRecord.timestamp <= until)

    # ── Count + paginate ──────────────────────────────────────────────────────
    total = query.count()
    rows = (
        query.order_by(SensorEventRecord.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # ── Enrich with entity names ───────────────────────────────────────────────
    entity_ids = list({r.resolved_entity_id for r in rows if r.resolved_entity_id})
    entity_name_map: dict = {}
    if entity_ids:
        profiles = (
            db.query(EntityProfile.entity_id, EntityProfile.name)
            .filter(EntityProfile.entity_id.in_(entity_ids))
            .all()
        )
        entity_name_map = {p.entity_id: p.name for p in profiles}

    items = [
        SensorEventResponse(
            event_id=r.event_id,
            sensor_type=r.sensor_type,
            event_type=r.event_type,
            timestamp=r.timestamp,
            zone_id=r.zone_id,
            raw_identifier=r.raw_identifier,
            identifier_type=r.identifier_type,
            resolved_entity_id=r.resolved_entity_id,
            entity_name=entity_name_map.get(r.resolved_entity_id) if r.resolved_entity_id else None,
            confidence=r.confidence,
            source_device_id=r.source_device_id,
            building=r.building,
            floor=r.floor,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return SensorEventListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
