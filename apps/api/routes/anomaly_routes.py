"""
Anomaly routes — bridges the alerts table to the /api/v1/anomalies/* API.

The frontend's anomaly dashboard calls /api/v1/anomalies/summary and
/api/v1/anomalies/all.  All anomaly data is already stored in the alerts
table by EventIngestionService → AlertService; this router exposes it under
the expected prefix without duplicating any storage.

GET /api/v1/anomalies/summary  → aggregated counts by severity / type / zone
GET /api/v1/anomalies/all      → paginated list (limit / offset query params)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth.dependencies import require_staff
from auth.models import AuthenticatedUser
from database.connection import get_db
from models.db.alerts import Alert

router = APIRouter(prefix="/api/v1/anomalies", tags=["anomalies"])


def _alert_to_anomaly(a: Alert) -> dict:
    loc = a.location or {}
    entities = a.affected_entities or []
    sev = a.severity.value if hasattr(a.severity, "value") else a.severity
    return {
        "id": str(a.id),
        "type": a.anomaly_type,
        "severity": sev,
        "location": loc.get("zone_id") or loc.get("building") or "unknown",
        "timestamp": a.created_at.isoformat() if a.created_at else None,
        "description": a.description,
        "details": a.evidence or {},
        "entity_id": entities[0] if entities else None,
        "recommended_actions": [],
    }


@router.get("/summary")
async def get_anomaly_summary(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> dict:
    """Aggregate counts of all real (non-mock) alerts by severity, type, and zone."""
    base = Alert.is_mock == False  # noqa: E712

    total: int = db.query(func.count(Alert.id)).filter(base).scalar() or 0

    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for count, sev in (
        db.query(func.count(), Alert.severity).filter(base).group_by(Alert.severity).all()
    ):
        key = sev.value if hasattr(sev, "value") else sev
        by_severity[key] = by_severity.get(key, 0) + count

    by_type: dict = {}
    for count, atype in (
        db.query(func.count(), Alert.anomaly_type)
        .filter(base, Alert.anomaly_type != None)  # noqa: E711
        .group_by(Alert.anomaly_type)
        .all()
    ):
        by_type[atype] = count

    zone_expr = func.json_extract_path_text(Alert.location, "zone_id")
    by_location: dict = {}
    for count, zone in (
        db.query(func.count(), zone_expr).filter(base).group_by(zone_expr).all()
    ):
        by_location[zone or "unknown"] = count

    return {
        "success": True,
        "data": {
            "total_anomalies": total,
            "by_severity": by_severity,
            "by_type": by_type,
            "by_location": by_location,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/all")
async def get_all_anomalies(
    limit: Optional[int] = Query(None, ge=0, description="Max results; omit for all"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> dict:
    """Paginated list of all real (non-mock) alerts, newest first."""
    q = (
        db.query(Alert)
        .filter(Alert.is_mock == False)  # noqa: E712
        .order_by(Alert.created_at.desc())
    )
    total = q.count()
    rows = q.offset(offset).limit(limit).all() if limit is not None else q.offset(offset).all()
    return {
        "success": True,
        "data": {
            "anomalies": [_alert_to_anomaly(a) for a in rows],
            "pagination": {
                "total_count": total,
                "returned_count": len(rows),
                "offset": offset,
                "limit": limit,
            },
            "detection_time": datetime.now(timezone.utc).isoformat(),
        },
    }
