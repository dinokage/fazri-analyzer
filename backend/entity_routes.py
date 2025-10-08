# backend/app/api/entity_routes.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from services.entity_resolver import get_resolver
from services.confidence_scorer import ConfidenceScorer
from models.entity import Entity

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
async def search_entity(request: EntitySearchRequest):
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
    threshold: float = Query(0.85, ge=0.0, le=1.0)
):
    """Fuzzy name search"""
    resolver = get_resolver()
    matches = resolver.resolve_by_fuzzy_name(name, threshold)
    
    return {
        "query": name,
        "threshold": threshold,
        "matches": [
            {
                "entity": match[0],
                "similarity": match[1]
            }
            for match in matches[:10]  # Top 10
        ]
    }

@router.get("/{entity_id}")
async def get_entity(entity_id: str):
    """Get entity by ID"""
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
    entity_type: Optional[str] = Query(None, description="Filter by role")
):
    """List all entities"""
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
async def get_entity_fusion_report(entity_id: str):
    """
    Get detailed multi-modal fusion report for an entity
    Shows all data sources, identifiers, and confidence scores
    """
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