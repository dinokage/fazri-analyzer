# backend/app/api/graph_routes.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from services.graph_builder import get_graph_builder
from services.timeline_service import TimelineService
from services.pattern_detection import PatternDetector
from services.ml_predictor import LocationPredictor
from pathlib import Path

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

@router.get("/timeline/{entity_id}")
async def get_entity_timeline(
    entity_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
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
    timestamp: Optional[str] = None
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
    hours: int = Query(12, ge=1, le=72, description="Hours since last activity")
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
async def get_graph_stats():
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
    end_date: Optional[str] = None
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
    gap_threshold_hours: int = Query(2, ge=1, le=24)
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
    days: int = Query(7, ge=1, le=30)
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
    date: Optional[str] = None
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
    
@router.get("/timeline/{entity_id}/patterns")
async def detect_activity_patterns(
    entity_id: str,
    days: int = Query(7, ge=1, le=30)
):
    """
    Detect activity patterns and routines
    """
    graph = get_graph_builder()
    
    # Get recent events
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    events = graph.get_entity_timeline(
        entity_id,
        start_date.isoformat(),
        end_date.isoformat()
    )
    
    if not events:
        raise HTTPException(status_code=404, detail="No activity found for entity")
    
    try:
        patterns = PatternDetector.detect_routine(events, days)
        prediction = PatternDetector.predict_next_location(events)
        
        return {
            'entity_id': entity_id,
            'analysis_period': f'Last {days} days',
            'patterns': patterns,
            'next_location_prediction': prediction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/predict/location/{entity_id}")
async def predict_location(
    entity_id: str,
    target_time: Optional[str] = None,
    lookback_days: int = Query(7, ge=1, le=30)
):
    """
    Predict entity location at target time using ML
    
    Args:
        entity_id: Entity to predict for
        target_time: ISO timestamp to predict (default: now)
        lookback_days: Days of history to use for prediction
    """
    if not target_time:
        target_datetime = datetime.now(timezone.utc)
    else:
        target_datetime = datetime.fromisoformat(target_time)
        # Ensure target_datetime is timezone-aware
        if target_datetime.tzinfo is None:
            target_datetime = target_datetime.replace(tzinfo=timezone.utc)
    
    graph = get_graph_builder()
    
    # Get recent events
    start_date = target_datetime - timedelta(days=lookback_days)
    events = graph.get_entity_timeline(
        entity_id,
        start_date.isoformat(),
        target_datetime.isoformat()
    )
    
    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No recent activity found for entity {entity_id}"
        )
    
    try:
        # Try to load trained model
        models_dir = Path(__file__).parent.parent.parent / 'models'
        model_path = models_dir / f"predictor_{entity_id}.pkl"
        
        predictor = LocationPredictor()
        
        if model_path.exists():
            predictor.load_model(model_path)
            print(f"Loaded trained model for {entity_id}")
        else:
            # Train on-the-fly if no saved model
            print(f"Training new model for {entity_id}")
            train_result = predictor.train(events)
            if not train_result['success']:
                # Fall back to rule-based
                pass
        
        # Make prediction
        prediction = predictor.predict(target_datetime, events, top_k=3)
        
        return {
            'entity_id': entity_id,
            **prediction
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/gap/{entity_id}")
async def predict_during_gap(
    entity_id: str,
    gap_start: str,
    gap_end: str
):
    """
    Predict locations during an activity gap
    
    Args:
        entity_id: Entity ID
        gap_start: Gap start time (ISO format)
        gap_end: Gap end time (ISO format)
    """
    gap_start_dt = datetime.fromisoformat(gap_start)
    gap_end_dt = datetime.fromisoformat(gap_end)
    # Get events before gap
    lookback_start = gap_start_dt - timedelta(days=7)
    
    graph = get_graph_builder()
    events = graph.get_entity_timeline(
        entity_id,
        lookback_start.isoformat(),
        gap_start
    )
    
    if not events:
        raise HTTPException(
            status_code=404,
            detail="No events before gap for prediction"
        )
    
    try:
        # Load or train predictor
        models_dir = Path(__file__).parent.parent.parent / 'models'
        model_path = models_dir / f"predictor_{entity_id}.pkl"
        
        predictor = LocationPredictor()
        
        if model_path.exists():
            predictor.load_model(model_path)
        else:
            train_result = predictor.train(events)
            if not train_result['success']:
                raise HTTPException(status_code=400, detail="Insufficient data for prediction")
        
        # Predict at multiple points during gap
        gap_duration = (gap_end_dt - gap_start_dt).total_seconds() / 3600  # hours
        
        if gap_duration <= 2:
            # Short gap, predict at midpoint
            prediction_times = [gap_start_dt + timedelta(hours=gap_duration/2)]
        else:
            # Longer gap, predict at multiple points
            num_predictions = min(5, int(gap_duration))
            prediction_times = [
                gap_start_dt + timedelta(hours=i * gap_duration / (num_predictions + 1))
                for i in range(1, num_predictions + 1)
            ]
        
        predictions = []
        for pred_time in prediction_times:
            result = predictor.predict(pred_time, events, top_k=1)
            if result['predictions']:
                predictions.append({
                    'time': pred_time.isoformat(),
                    **result['predictions'][0]
                })
        
        return {
            'entity_id': entity_id,
            'gap_start': gap_start,
            'gap_end': gap_end,
            'gap_duration_hours': round(gap_duration, 2),
            'predictions': predictions
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))