# backend/app/api/entity_routes.py
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.entity_resolver import get_resolver
from services.confidence_scorer import ConfidenceScorer
from models.entity import Entity
from auth.dependencies import get_current_user, require_staff
from auth.models import AuthenticatedUser, UserRole
from auth.exceptions import PermissionDeniedError
from database.connection import get_db

router = APIRouter(prefix="/api/v1/entities", tags=["entities"])

class EntitySearchRequest(BaseModel):
    identifier_type: str
    identifier_value: str

class EntitySearchResponse(BaseModel):
    entity: Optional[Entity]
    all_identifiers: dict
    linked_entities: List[Entity]
    confidence: float

@router.post("/search", response_model=EntitySearchResponse)
async def search_entity(
    request: EntitySearchRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Search for entity by identifier"""
    resolver = get_resolver()
    
    # Direct resolution
    entity = resolver.resolve_by_identifier(
        request.identifier_type,
        request.identifier_value
    )
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Get all identifiers
    all_ids = resolver.get_all_identifiers_for_entity(entity.entity_id)
    
    # Get linked entities
    linked = resolver.resolve_transitive(entity.entity_id)
    
    return EntitySearchResponse(
        entity=entity,
        all_identifiers=all_ids,
        linked_entities=linked,
        confidence=entity.confidence_score
    )

@router.get("/fuzzy-search")
async def fuzzy_search_by_name(
    name: str = Query(..., description="Name to search"),
    threshold: float = Query(0.85, ge=0.0, le=1.0),
    current_user: AuthenticatedUser = Depends(require_staff()),
    db: Session = Depends(get_db),
):
    """Fuzzy name search across auth users and staff_profiles (STAFF+ only)"""
    from sqlalchemy import create_engine, text
    from config import settings

    seen_entity_ids: set = set()
    matches = []

    # ── 1. Query auth service user table ──────────────────────────────────────
    if settings.AUTH_DATABASE_URL:
        try:
            auth_engine = create_engine(settings.AUTH_DATABASE_URL, pool_pre_ping=True)
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
                seen_entity_ids.add(row.entity_id)
                matches.append({
                    "entity": {
                        "entity_id": row.entity_id,
                        "name": row.name,
                        "entity_type": row.role.lower() if row.role else "student",
                        "department": row.department,
                        "face_id": row.face_id,
                    },
                    "similarity": 1.0,
                })
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Auth DB fuzzy-search failed: %s", exc)

    # ── 2. Query staff_profiles (non-mock, with entity_id) ────────────────────
    from models.db.alerts import StaffProfile

    from sqlalchemy import or_
    staff_list = (
        db.query(StaffProfile)
        .filter(or_(StaffProfile.name.ilike(f"%{name}%"), StaffProfile.entity_id.ilike(f"%{name}%")))
        .filter(StaffProfile.is_mock_user == False)
        .filter(StaffProfile.entity_id.isnot(None))
        .order_by(StaffProfile.name)
        .limit(20)
        .all()
    )
    for s in staff_list:
        if not s.name or s.entity_id in seen_entity_ids:
            continue
        matches.append({
            "entity": {
                "entity_id": s.entity_id,
                "name": s.name,
                "entity_type": s.role.value if s.role else "staff",
                "department": s.department,
                "face_id": None,
            },
            "similarity": 1.0,
        })

    matches.sort(key=lambda m: m["entity"]["name"])

    return {
        "query": name,
        "threshold": threshold,
        "matches": matches[:20],
    }

@router.get("/{entity_id}")
async def get_entity(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get entity by ID (students can only access their own data)"""
    # Students can only access their own entity
    if current_user.role == UserRole.STUDENT and current_user.entity_id != entity_id:
        raise PermissionDeniedError("You can only access your own data")

    resolver = get_resolver()

    if entity_id not in resolver.entities:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    entity = resolver.entities[entity_id]
    all_ids = resolver.get_all_identifiers_for_entity(entity_id)
    linked = resolver.resolve_transitive(entity_id)
    
    return {
        "entity": entity,
        "all_identifiers": all_ids,
        "linked_entities": linked
    }

@router.get("/")
async def list_entities(
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = Query(None, description="Filter by department"),
    entity_type: Optional[str] = Query(None, description="Filter by role"),
    current_user: AuthenticatedUser = Depends(require_staff())
):
    """List all entities (STAFF+ only)"""
    resolver = get_resolver()
    entities = list(resolver.entities.values())
    if department and entity_type:
        entities = [e for e in entities if e.department == department and e.entity_type == entity_type][skip:skip+limit]
    elif department:
        entities = [e for e in entities if e.department == department][skip:skip+limit]
    elif entity_type:
        entities = [e for e in entities if e.entity_type == entity_type][skip:skip+limit]
    else:
        entities = entities[skip:skip+limit]
    return {
        "total": len(resolver.entities),
        "skip": skip,
        "limit": limit,
        "entities": entities
    }

@router.get("/{entity_id}/fusion-report")
async def get_entity_fusion_report(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get detailed multi-modal fusion report for an entity
    Shows all data sources, identifiers, and confidence scores
    (students can only access their own data)
    """
    # Students can only access their own entity
    if current_user.role == UserRole.STUDENT and current_user.entity_id != entity_id:
        raise PermissionDeniedError("You can only access your own data")

    resolver = get_resolver()

    if entity_id not in resolver.entities:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    entity = resolver.entities[entity_id]
    
    # Get all identifiers grouped by source
    identifiers_by_source = {}
    for identifier in entity.identifiers:
        source = identifier.source
        if source not in identifiers_by_source:
            identifiers_by_source[source] = []
        
        identifiers_by_source[source].append({
            'type': identifier.type,
            'value': identifier.value,
            'confidence': identifier.confidence,
            'first_seen': identifier.first_seen,
            'last_seen': identifier.last_seen
        })
    
    # Get linked entities with confidence scores
    linked = resolver.resolve_transitive(entity_id)
    linked_with_confidence = []
    
    for linked_entity in linked:
        # Find shared identifiers
        shared = []
        for id1 in entity.identifiers:
            for id2 in linked_entity.identifiers:
                if id1.type == id2.type and id1.value == id2.value:
                    shared.append(f"{id1.type}:{id1.value}")
        
        entity1_ids = [{'type': id.type, 'source': id.source} for id in entity.identifiers]
        entity2_ids = [{'type': id.type, 'source': id.source} for id in linked_entity.identifiers]
        
        link_confidence = ConfidenceScorer.calculate_link_confidence(
            entity1_ids, entity2_ids, shared
        )
        
        linked_with_confidence.append({
            'entity_id': linked_entity.entity_id,
            'name': linked_entity.name,
            'confidence': link_confidence,
            'shared_identifiers': shared
        })
    
    # Sort by confidence
    linked_with_confidence.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Get provenance
    provenance = entity.get_provenance()
    
    return {
        'entity_id': entity.entity_id,
        'name': entity.name,
        'overall_confidence': entity.confidence_score,
        'identifiers_by_source': identifiers_by_source,
        'provenance': provenance,
        'linked_entities': linked_with_confidence,
        'fusion_summary': {
            'total_sources': len(identifiers_by_source),
            'total_identifiers': len(entity.identifiers),
            'identifier_types': list(set([id.type for id in entity.identifiers])),
            'most_reliable_source': max(identifiers_by_source.items(), 
                                       key=lambda x: len(x[1]))[0] if identifiers_by_source else None
        }
    }