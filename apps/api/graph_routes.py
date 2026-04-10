# backend/app/api/graph_routes.py
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from services.graph_builder import get_graph_builder
from services.timeline_service import TimelineService
from auth.dependencies import require_staff
from auth.models import AuthenticatedUser

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

@router.get("/timeline/{entity_id}")
async def get_entity_timeline(
    entity_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_staff())
):
    """Get chronological timeline for entity"""
    graph = get_graph_builder()
    
    try:
        events = graph.get_entity_timeline(entity_id, start_date, end_date)
        
        return {
            "entity_id": entity_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_events": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/location/{location_id}/entities")
async def get_entities_at_location(
    location_id: str,
    timestamp: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_staff())
):
    """Find entities at location at specific time"""
    graph = get_graph_builder()
    
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    
    try:
        entities = graph.find_entities_at_location(location_id, timestamp)
        
        return {
            "location_id": location_id,
            "timestamp": timestamp,
            "entity_count": len(entities),
            "entities": entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/missing")
async def get_missing_entities(
    hours: int = Query(12, ge=1, le=72, description="Hours since last activity"),
    current_user: AuthenticatedUser = Depends(require_staff())
):
    """Find entities with no activity in last N hours"""
    graph = get_graph_builder()
    
    try:
        missing = graph.find_missing_entities(hours)
        
        return {
            "threshold_hours": hours,
            "alert_count": len(missing),
            "missing_entities": missing
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_graph_stats(
    current_user: AuthenticatedUser = Depends(require_staff())
):
    """Get database statistics"""
    graph = get_graph_builder()
    
    query = """
    MATCH (e:Entity) WITH count(e) as entity_count
    MATCH (ev:Event) WITH entity_count, count(ev) as event_count
    MATCH (l:Location) WITH entity_count, event_count, count(l) as location_count
    MATCH ()-[r:SAME_AS]->() WITH entity_count, event_count, location_count, count(r) as relationship_count
    RETURN entity_count, event_count, location_count, relationship_count
    """
    
    try:
        with graph.driver.session() as session:
            result = session.run(query)
            record = result.single()
            
            return {
                "entities": record['entity_count'],
                "events": record['event_count'],
                "locations": record['location_count'],
                "relationships": record['relationship_count']
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/timeline/{entity_id}/summary")
async def get_timeline_summary(
    entity_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_staff())
):
    """
    Get human-readable timeline summary
    """
    graph = get_graph_builder()
    timeline_service = TimelineService(graph)
    
    try:
        summary = timeline_service.generate_summary(entity_id, start_date, end_date)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timeline/{entity_id}/with-gaps")
async def get_timeline_with_gaps(
    entity_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    gap_threshold_hours: int = Query(2, ge=1, le=24),
    current_user: AuthenticatedUser = Depends(require_staff())
):
    """
    Get timeline with gap detection
    """
    graph = get_graph_builder()
    timeline_service = TimelineService(graph)
    
    try:
        result = timeline_service.get_timeline_with_gaps(
            entity_id, start_date, end_date, gap_threshold_hours
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timeline/{entity_id}/heatmap")
async def get_activity_heatmap(
    entity_id: str,
    days: int = Query(7, ge=1, le=30),
    current_user: AuthenticatedUser = Depends(require_staff())
):
    """
    Get activity heatmap data for visualization
    """
    graph = get_graph_builder()
    timeline_service = TimelineService(graph)
    
    try:
        heatmap = timeline_service.get_activity_heatmap(entity_id, days)
        return heatmap
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timeline/{entity_id}/daily-summary")
async def get_daily_summary(
    entity_id: str,
    date: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_staff())
):
    """
    Get detailed summary for a specific day
    """
    if not date:
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Parse date
    target_date = datetime.strptime(date, '%Y-%m-%d')
    start_date = target_date.isoformat()
    end_date = (target_date + timedelta(days=1)).isoformat()
    
    graph = get_graph_builder()
    timeline_service = TimelineService(graph)
    
    try:
        summary = timeline_service.generate_summary(entity_id, start_date, end_date)
        return {
            'date': date,
            'entity_id': entity_id,
            'summary': summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
