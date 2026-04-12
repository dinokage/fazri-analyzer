"""
Spatial / zone routes.

Serves zone metadata from ZONES_DATA (in-memory) and real-time occupancy
derived from the sensor_events table.

GET /api/v1/spatial/zones                        → list all zones
GET /api/v1/spatial/zones/{zone_id}              → zone detail
GET /api/v1/spatial/zones/{zone_id}/occupancy    → real-time occupancy
GET /api/v1/spatial/zones/{zone_id}/history      → hourly event counts (last 24h)
GET /api/v1/spatial/zones/{zone_id}/connections  → adjacent zones via travel matrix
GET /api/v1/spatial/campus/summary               → campus-wide aggregate
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth.dependencies import require_staff, require_org_member
from auth.models import AuthenticatedUser
from database.connection import get_db
from scripts.sample_zones import ZONES_DATA

logger = logging.getLogger(__name__)

MAX_HOURS_BACK = 168  # 7 days

router = APIRouter(prefix="/api/v1/spatial", tags=["spatial"])

# ─── In-memory zone index ────────────────────────────────────────────────────

_ZONES: Dict[str, Dict] = {z["zone_id"]: z for z in ZONES_DATA}

# Entity is "present" in a zone if seen within this window
_PRESENCE_WINDOW_MINUTES = 30

# Zones reachable within this travel time are considered "connected"
_CONNECTION_THRESHOLD_SECONDS = 120


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _occupancy_status(rate: float) -> str:
    if rate >= 0.9:
        return "full"
    if rate >= 0.7:
        return "crowded"
    return "normal"


def _zone_occupancy_dict(zone_id: str, db: Session) -> Dict:
    """Count entities whose *latest* event in the window places them in this zone."""
    since = datetime.now(timezone.utc) - timedelta(minutes=_PRESENCE_WINDOW_MINUTES)
    count = db.execute(
        text("""
            WITH latest AS (
                SELECT DISTINCT ON (resolved_entity_id)
                    resolved_entity_id, zone_id, event_type
                FROM sensor_events
                WHERE resolved_entity_id IS NOT NULL
                  AND timestamp >= :since
                ORDER BY resolved_entity_id, timestamp DESC
            )
            SELECT COUNT(*) FROM latest
            WHERE zone_id = :zone_id
              AND event_type IN (
                'ACCESS_GRANTED', 'DEVICE_ASSOCIATED', 'ENTRY', 'FACE_RECOGNIZED'
              )
        """),
        {"zone_id": zone_id, "since": since},
    ).scalar() or 0

    zone = _ZONES.get(zone_id, {})
    capacity = zone.get("capacity", 100)
    rate = round(min(count / capacity, 1.0), 4) if capacity > 0 else 0.0

    return {
        "zone_id": zone_id,
        "zone_name": zone.get("name", zone_id),
        "current_occupancy": count,
        "capacity": capacity,
        "occupancy_rate": rate,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "status": _occupancy_status(rate),
    }


def _zone_to_dict(zone: Dict) -> Dict:
    """Normalise a ZONES_DATA entry to the frontend Zone shape."""
    return {
        "zone_id":     zone["zone_id"],
        "name":        zone["name"],
        "zone_type":   zone["zone_type"],
        "capacity":    zone["capacity"],
        "building":    zone["building"],
        "floor":       zone.get("floor", 1),
        "coordinates": zone.get("coordinates"),
        "department":  zone.get("department"),
        "description": zone.get("description"),
        "operating_hours": zone.get("operating_hours"),
        "facilities":  zone.get("facilities", []),
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/zones")
async def list_zones(
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> Dict:
    zones = [_zone_to_dict(z) for z in ZONES_DATA]
    return {"success": True, "data": zones, "count": len(zones)}


@router.get("/zones/{zone_id}")
async def get_zone(
    zone_id: str,
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> Dict:
    zone = _ZONES.get(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
    return {"success": True, "data": _zone_to_dict(zone)}


@router.get("/zones/{zone_id}/occupancy")
async def get_zone_occupancy(
    zone_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> Dict:
    if zone_id not in _ZONES:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
    return {"success": True, "data": _zone_occupancy_dict(zone_id, db)}


@router.get("/zones/{zone_id}/history")
async def get_zone_history(
    zone_id: str,
    hours_back: int = 24,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> Dict:
    """Return hourly event counts for the zone over the past N hours."""
    if hours_back <= 0 or hours_back > MAX_HOURS_BACK:
        raise HTTPException(
            status_code=400,
            detail=f"hours_back must be between 1 and {MAX_HOURS_BACK}",
        )
    if zone_id not in _ZONES:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    rows = db.execute(
        text("""
            SELECT
                date_trunc('hour', timestamp) AS hour,
                COUNT(*)                      AS event_count,
                COUNT(DISTINCT resolved_entity_id) FILTER (
                    WHERE resolved_entity_id IS NOT NULL
                )                             AS unique_entities
            FROM sensor_events
            WHERE zone_id   = :zone_id
              AND timestamp >= :since
            GROUP BY 1
            ORDER BY 1
        """),
        {"zone_id": zone_id, "since": since},
    ).all()

    history = [
        {
            "timestamp": row.hour.isoformat(),
            "event_count": row.event_count,
            "unique_entities": row.unique_entities,
        }
        for row in rows
    ]
    return {"success": True, "data": history}


@router.get("/zones/{zone_id}/connections")
async def get_zone_connections(
    zone_id: str,
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> Dict:
    """Return zones adjacent to zone_id based on travel-time matrix."""
    if zone_id not in _ZONES:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

    try:
        from config.zone_matrix import zone_matrix
        connections = []
        for other_id, other_zone in _ZONES.items():
            if other_id == zone_id:
                continue
            travel_seconds = zone_matrix.get_min_travel_time(zone_id, other_id)
            if travel_seconds <= _CONNECTION_THRESHOLD_SECONDS:
                connections.append({
                    "zone_id":        other_id,
                    "name":           other_zone["name"],
                    "building":       other_zone["building"],
                    "travel_seconds": travel_seconds,
                })
        connections.sort(key=lambda x: x["travel_seconds"])
    except Exception as exc:
        logger.warning("Zone matrix unavailable: %s", exc)
        connections = []

    return {"success": True, "data": connections}


@router.get("/campus/summary")
async def get_campus_summary(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> Dict:
    """Aggregate real-time occupancy across all zones."""
    since = datetime.now(timezone.utc) - timedelta(minutes=_PRESENCE_WINDOW_MINUTES)

    # Fetch occupancy counts using latest-event-per-entity so entities moving
    # between zones are counted only in their current zone.
    rows = db.execute(
        text("""
            WITH latest AS (
                SELECT DISTINCT ON (resolved_entity_id)
                    resolved_entity_id, zone_id, event_type
                FROM sensor_events
                WHERE resolved_entity_id IS NOT NULL
                  AND timestamp >= :since
                ORDER BY resolved_entity_id, timestamp DESC
            )
            SELECT zone_id, COUNT(*) AS cnt
            FROM latest
            WHERE event_type IN (
                'ACCESS_GRANTED', 'DEVICE_ASSOCIATED', 'ENTRY', 'FACE_RECOGNIZED'
            )
            GROUP BY zone_id
        """),
        {"since": since},
    ).all()

    occupancy_map: Dict[str, int] = {row.zone_id: row.cnt for row in rows}

    total_capacity = 0
    total_occupancy = 0
    zone_details: List[Dict] = []

    for z in ZONES_DATA:
        zid = z["zone_id"]
        cap = z["capacity"]
        occ = occupancy_map.get(zid, 0)
        total_capacity += cap
        total_occupancy += occ
        zone_details.append({
            "zone_id":          zid,
            "zone_name":        z["name"],
            "zone_type":        z["zone_type"],
            "capacity":         cap,
            "current_occupancy": occ,
        })

    overall_rate = round(total_occupancy / total_capacity, 4) if total_capacity > 0 else 0.0

    zone_details_sorted = sorted(zone_details, key=lambda x: x["current_occupancy"], reverse=True)
    high_traffic = [z for z in zone_details_sorted if z["current_occupancy"] > 0][:5]
    underutilized = [z for z in zone_details_sorted if z["current_occupancy"] == 0][:5]

    return {
        "success": True,
        "data": {
            "summary": {
                "total_zones":            len(ZONES_DATA),
                "total_capacity":         total_capacity,
                "total_occupancy":        total_occupancy,
                "overall_occupancy_rate": overall_rate,
                "status":                 _occupancy_status(overall_rate),
            },
            "zone_details":      zone_details_sorted,
            "high_traffic_zones":  high_traffic,
            "underutilized_zones": underutilized,
            "last_updated":      datetime.now(timezone.utc).isoformat(),
        },
    }
