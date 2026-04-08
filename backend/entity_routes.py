# backend/app/api/entity_routes.py
import difflib
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, List, Dict

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, require_staff
from auth.exceptions import PermissionDeniedError
from auth.models import AuthenticatedUser, UserRole
from config import settings
from database.connection import get_db
from models.db.entity_identifiers import EntityIdentifier
from models.db.entity_profiles import EntityProfile
from services.confidence_scorer import ConfidenceScorer
from services.entity_resolution_service import EntityProfileDTO, get_entity_resolution_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB-backed helpers (replace the in-memory resolver methods)
# ---------------------------------------------------------------------------

def _identifiers_for_entity(entity_id: str, db: Session) -> List[EntityIdentifier]:
    """Return all active identifier rows for an entity."""
    return (
        db.query(EntityIdentifier)
        .filter_by(entity_id=entity_id, active=True)
        .all()
    )


def _all_identifiers_grouped(entity_id: str, db: Session) -> Dict[str, List[str]]:
    """Return identifiers grouped by type: {identifier_type: [values, ...]}."""
    rows = _identifiers_for_entity(entity_id, db)
    grouped: Dict[str, List[str]] = defaultdict(list)
    for r in rows:
        grouped[r.identifier_type].append(r.identifier_value)
    return dict(grouped)


def _transitive_entities(entity_id: str, db: Session) -> List[EntityProfileDTO]:
    """Find other entities that share any identifier with entity_id."""
    rows = db.execute(
        sa_text(
            """
            SELECT DISTINCT ei2.entity_id
            FROM   entity_identifiers ei1
            JOIN   entity_identifiers ei2
                   ON  ei1.identifier_type  = ei2.identifier_type
                   AND ei1.identifier_value = ei2.identifier_value
            WHERE  ei1.entity_id = :eid
              AND  ei2.entity_id != :eid
              AND  ei1.active = true
              AND  ei2.active = true
            """
        ),
        {"eid": entity_id},
    ).fetchall()

    svc = get_entity_resolution_service()
    return [
        p
        for r in rows
        if (p := svc.get_entity_profile(r.entity_id, db=db)) is not None
    ]


def _profile_to_entity_dict(
    profile: EntityProfileDTO,
    identifiers: List[EntityIdentifier],
) -> dict:
    """Build an Entity-compatible response dict from DB data."""
    return {
        "entity_id": profile.entity_id,
        "name": profile.name,
        "email": profile.email,
        "entity_type": (profile.role or "unknown").lower(),
        "department": profile.department,
        "confidence_score": 1.0,
        "linked_entity_ids": [],
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "identifiers": [
            {
                "type": i.identifier_type,
                "value": i.identifier_value,
                "source": i.source,
                "confidence": i.confidence,
                "first_seen": i.first_seen.isoformat() if i.first_seen else None,
                "last_seen": i.last_seen.isoformat() if i.last_seen else None,
            }
            for i in identifiers
        ],
    }


# ---------------------------------------------------------------------------
# Name similarity helper (unchanged)
# ---------------------------------------------------------------------------

def _name_similarity(query: str, candidate: str) -> float:
    q = query.lower()
    n = candidate.lower()
    full = difflib.SequenceMatcher(None, q, n).ratio()
    word_best = max(
        (difflib.SequenceMatcher(None, q, word).ratio() for word in n.split()),
        default=0.0,
    )
    return max(full, word_best)


# ---------------------------------------------------------------------------
# Router and auth DB engine
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/entities", tags=["entities"])

_auth_engine = None


def _get_auth_engine():
    global _auth_engine
    if _auth_engine is None:
        from sqlalchemy import create_engine
        if settings.AUTH_DATABASE_URL:
            _auth_engine = create_engine(settings.AUTH_DATABASE_URL, pool_pre_ping=True)
    return _auth_engine


class EntitySearchRequest(BaseModel):
    identifier_type: str
    identifier_value: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/search")
async def search_entity(
    request: EntitySearchRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search for an entity by any identifier type (card_id, mac_address, …)."""
    svc = get_entity_resolution_service()
    profile = svc.resolve(request.identifier_type, request.identifier_value, db=db)
    if profile is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    if current_user.role == UserRole.STUDENT and current_user.entity_id != profile.entity_id:
        raise PermissionDeniedError("You can only access your own data")

    identifiers = _identifiers_for_entity(profile.entity_id, db)
    entity_dict = _profile_to_entity_dict(profile, identifiers)
    all_ids = _all_identifiers_grouped(profile.entity_id, db)
    linked = [
        _profile_to_entity_dict(p, _identifiers_for_entity(p.entity_id, db))
        for p in _transitive_entities(profile.entity_id, db)
    ]

    return {
        "entity": entity_dict,
        "all_identifiers": all_ids,
        "linked_entities": linked,
        "confidence": 1.0,
    }


@router.get("/fuzzy-search")
async def fuzzy_search_by_name(
    name: str = Query(..., description="Name to search"),
    threshold: float = Query(0.85, ge=0.0, le=1.0),
    current_user: AuthenticatedUser = Depends(require_staff()),
    db: Session = Depends(get_db),
):
    """Fuzzy name search across auth users and staff_profiles (STAFF+ only)."""
    from sqlalchemy import text

    seen_entity_ids: set = set()
    matches = []

    # ── 1. Query auth service user table ──────────────────────────────────────
    auth_engine = _get_auth_engine()
    if auth_engine is not None:
        try:
            with auth_engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT entity_id, name, role, department, face_id "
                        'FROM "user" '
                        "WHERE name ILIKE :pattern OR entity_id ILIKE :pattern "
                        "ORDER BY name LIMIT 20"
                    ),
                    {"pattern": f"%{name}%"},
                ).fetchall()
            for row in rows:
                if not row.entity_id:
                    continue
                similarity = max(
                    _name_similarity(name, row.name) if row.name else 0.0,
                    _name_similarity(name, row.entity_id),
                )
                if similarity < threshold:
                    continue
                seen_entity_ids.add(row.entity_id)
                matches.append({
                    "entity": {
                        "entity_id": row.entity_id,
                        "name": row.name,
                        "entity_type": row.role.lower() if row.role else "student",
                        "department": row.department,
                        "face_id": row.face_id,
                    },
                    "similarity": round(similarity, 4),
                })
        except Exception as exc:
            logger.warning("Auth DB fuzzy-search failed: %s", exc)

    # ── 2. Query staff_profiles (non-mock, with entity_id) ────────────────────
    from models.db.alerts import StaffProfile
    from sqlalchemy import or_

    staff_list = (
        db.query(StaffProfile)
        .filter(or_(StaffProfile.name.ilike(f"%{name}%"), StaffProfile.entity_id.ilike(f"%{name}%")))
        .filter(StaffProfile.is_mock_user.is_(False))
        .filter(StaffProfile.entity_id.isnot(None))
        .order_by(StaffProfile.name)
        .limit(20)
        .all()
    )
    for s in staff_list:
        if not s.name or s.entity_id in seen_entity_ids:
            continue
        similarity = max(
            _name_similarity(name, s.name),
            _name_similarity(name, s.entity_id),
        )
        if similarity < threshold:
            continue
        matches.append({
            "entity": {
                "entity_id": s.entity_id,
                "name": s.name,
                "entity_type": s.role.value if s.role else "staff",
                "department": s.department,
                "face_id": None,
            },
            "similarity": round(similarity, 4),
        })

    matches.sort(key=lambda m: m["entity"]["name"])

    return {
        "query": name,
        "threshold": threshold,
        "matches": matches[:20],
    }


@router.get("/{entity_id}/fusion-report")
async def get_entity_fusion_report(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Multi-modal fusion report for an entity.
    Students can only access their own data.
    """
    if current_user.role == UserRole.STUDENT and current_user.entity_id != entity_id:
        raise PermissionDeniedError("You can only access your own data")

    svc = get_entity_resolution_service()
    profile = svc.get_entity_profile(entity_id, db=db)
    if profile is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    identifiers = _identifiers_for_entity(entity_id, db)

    # Group by source for the identifiers_by_source section
    identifiers_by_source: Dict[str, List[dict]] = defaultdict(list)
    for i in identifiers:
        identifiers_by_source[i.source].append({
            "type": i.identifier_type,
            "value": i.identifier_value,
            "confidence": i.confidence,
            "first_seen": i.first_seen.isoformat() if i.first_seen else None,
            "last_seen": i.last_seen.isoformat() if i.last_seen else None,
        })

    # Provenance: {source: ["type:value", ...]}
    provenance: Dict[str, List[str]] = defaultdict(list)
    for i in identifiers:
        provenance[i.source].append(f"{i.identifier_type}:{i.identifier_value}")

    # Transitive links with confidence scoring
    my_id_set = {(i.identifier_type, i.identifier_value) for i in identifiers}
    entity1_ids = [{"type": i.identifier_type, "source": i.source} for i in identifiers]

    linked_with_confidence = []
    for p in _transitive_entities(entity_id, db):
        p_identifiers = _identifiers_for_entity(p.entity_id, db)
        shared = [
            f"{i.identifier_type}:{i.identifier_value}"
            for i in p_identifiers
            if (i.identifier_type, i.identifier_value) in my_id_set
        ]
        entity2_ids = [{"type": i.identifier_type, "source": i.source} for i in p_identifiers]
        link_confidence = ConfidenceScorer.calculate_link_confidence(
            entity1_ids, entity2_ids, shared
        )
        linked_with_confidence.append({
            "entity_id": p.entity_id,
            "name": p.name,
            "confidence": link_confidence,
            "shared_identifiers": shared,
        })
    linked_with_confidence.sort(key=lambda x: x["confidence"], reverse=True)

    identifier_types = list({i.identifier_type for i in identifiers})
    most_reliable_source = (
        max(identifiers_by_source.items(), key=lambda x: len(x[1]))[0]
        if identifiers_by_source
        else None
    )

    return {
        "entity_id": profile.entity_id,
        "name": profile.name,
        "overall_confidence": 1.0,
        "identifiers_by_source": dict(identifiers_by_source),
        "provenance": dict(provenance),
        "linked_entities": linked_with_confidence,
        "fusion_summary": {
            "total_sources": len(identifiers_by_source),
            "total_identifiers": len(identifiers),
            "identifier_types": identifier_types,
            "most_reliable_source": most_reliable_source,
        },
    }


@router.get("/{entity_id}")
async def get_entity(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get entity by ID. Students can only access their own data."""
    if current_user.role == UserRole.STUDENT and current_user.entity_id != entity_id:
        raise PermissionDeniedError("You can only access your own data")

    svc = get_entity_resolution_service()
    profile = svc.get_entity_profile(entity_id, db=db)
    if profile is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    identifiers = _identifiers_for_entity(entity_id, db)
    entity_dict = _profile_to_entity_dict(profile, identifiers)
    all_ids = _all_identifiers_grouped(entity_id, db)
    linked = [
        _profile_to_entity_dict(p, _identifiers_for_entity(p.entity_id, db))
        for p in _transitive_entities(entity_id, db)
    ]

    return {
        "entity": entity_dict,
        "all_identifiers": all_ids,
        "linked_entities": linked,
    }


@router.get("/")
async def list_entities(
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = Query(None, description="Filter by department"),
    entity_type: Optional[str] = Query(None, description="Filter by role"),
    current_user: AuthenticatedUser = Depends(require_staff()),
    db: Session = Depends(get_db),
):
    """List all entities (STAFF+ only)."""
    query = db.query(EntityProfile)
    if department:
        query = query.filter(EntityProfile.department == department)
    if entity_type:
        query = query.filter(EntityProfile.role == entity_type)

    total = query.count()
    profiles = query.offset(skip).limit(limit).all()

    # Bulk-fetch identifiers to avoid N+1 queries
    entity_ids = [p.entity_id for p in profiles]
    all_idents = (
        db.query(EntityIdentifier)
        .filter(
            EntityIdentifier.entity_id.in_(entity_ids),
            EntityIdentifier.active == True,  # noqa: E712
        )
        .all()
    )
    ident_map: Dict[str, List[EntityIdentifier]] = defaultdict(list)
    for i in all_idents:
        ident_map[i.entity_id].append(i)

    entities = [
        _profile_to_entity_dict(EntityProfileDTO.from_orm(p), ident_map[p.entity_id])
        for p in profiles
    ]

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "entities": entities,
    }


@router.get("/{entity_id}/timeline")
async def get_entity_sensor_timeline(
    entity_id: str,
    since: Optional[str] = Query(None, description="ISO 8601 start timestamp (default: 7 days ago)"),
    limit: int = Query(200, ge=1, le=500),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the chronological sensor event history for one entity across all modalities.
    Also returns recent alert IDs associated with this entity so the frontend can
    highlight anomaly-triggering events.
    """
    from datetime import timedelta
    from models.db.sensor_events import SensorEventRecord
    from models.db.alerts import Alert

    # ── Students may only view their own timeline ─────────────────────────────
    if current_user.role == UserRole.STUDENT and current_user.entity_id != entity_id:
        raise PermissionDeniedError("You can only access your own timeline")

    # ── Resolve since timestamp ───────────────────────────────────────────────
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid 'since' timestamp") from e
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(days=7)

    if since_dt.tzinfo is None:
        since_dt = since_dt.replace(tzinfo=timezone.utc)

    # ── Sensor events for this entity ─────────────────────────────────────────
    rows = (
        db.query(SensorEventRecord)
        .filter(SensorEventRecord.resolved_entity_id == entity_id)
        .filter(SensorEventRecord.timestamp >= since_dt)
        .order_by(SensorEventRecord.timestamp.asc())
        .limit(limit)
        .all()
    )

    # ── Recent alerts referencing this entity ─────────────────────────────────
    alert_rows = []
    if settings.ALERT_SYSTEM_ENABLED:
        try:
            alert_rows = (
                db.query(Alert.id, Alert.anomaly_type, Alert.created_at)
                .filter(Alert.affected_entities.contains([entity_id]))
                .filter(Alert.created_at >= since_dt)
                .order_by(Alert.created_at.asc())
                .all()
            )
        except Exception as e:
            logger.warning("Alert query failed for entity %s since %s: %s", entity_id, since_dt, e)
            alert_rows = []

    alert_windows = [
        {
            "alert_id": str(a.id),
            "anomaly_type": a.anomaly_type,
            "timestamp": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alert_rows
    ]

    events_out = [
        {
            "event_id": r.event_id,
            "sensor_type": r.sensor_type,
            "event_type": r.event_type,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "zone_id": r.zone_id,
            "building": r.building,
            "floor": r.floor,
            "confidence": r.confidence,
            "source_device_id": r.source_device_id,
        }
        for r in rows
    ]

    return {
        "entity_id": entity_id,
        "since": since_dt.isoformat(),
        "total": len(events_out),
        "events": events_out,
        "alerts": alert_windows,
    }
