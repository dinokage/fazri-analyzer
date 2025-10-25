# backend/app/api/anomaly_routes.py - Updated with new endpoints
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta
from services.anomaly_detection import AnomalyDetectionService
from config import settings
import os
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/anomalies", tags=["anomaly-detection"])

# SQLAlchemy setup for cached anomalies
DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"
Base = declarative_base()

class Anomaly(Base):
    __tablename__ = 'anomalies'
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    recommended_actions = Column(JSON, nullable=True)
    entity_id = Column(String, nullable=True)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_anomaly_service():
    neo4j_uri = settings.NEO4J_URI
    neo4j_user = settings.NEO4J_USER
    neo4j_password = settings.NEO4J_PASSWORD
    
    return AnomalyDetectionService(neo4j_uri, neo4j_user, neo4j_password)

@router.get("/all")
async def get_all_historical_anomalies(
    limit: Optional[int] = Query(None, description="Limit number of results (default: no limit)"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """Get all anomalies from the cached dataset with optional pagination"""
    try:
        query = db.query(Anomaly)
        total_count = query.count()
        
        # Apply pagination
        if limit:
            paginated_anomalies = query.offset(offset).limit(limit).all()
        else:
            paginated_anomalies = query.offset(offset).all()
        
        # Convert to dicts
        anomalies_dict = [
            {
                "id": a.id,
                "type": a.type,
                "location": a.location,
                "severity": a.severity,
                "timestamp": a.timestamp.isoformat(),
                "description": a.description,
                "details": a.details,
                "recommended_actions": a.recommended_actions
            } for a in paginated_anomalies
        ]

        return {
            "success": True,
            "data": {
                "anomalies": anomalies_dict,
                "pagination": {
                    "total_count": total_count,
                    "returned_count": len(anomalies_dict),
                    "offset": offset,
                    "limit": limit
                },
                "time_range": "Entire dataset",
                "detection_time": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving all anomalies: {str(e)}")

@router.get("/date-range")
async def get_anomalies_by_date_range(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Get anomalies within a specific date range from the cache"""
    try:
        # Validate date format
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        query = db.query(Anomaly).filter(Anomaly.timestamp >= start_dt, Anomaly.timestamp <= end_dt)
        anomalies = query.all()
        
        anomalies_dict = [
            {
                "id": a.id,
                "type": a.type,
                "location": a.location,
                "severity": a.severity,
                "timestamp": a.timestamp.isoformat(),
                "description": a.description,
                "details": a.details,
                "recommended_actions": a.recommended_actions
            } for a in anomalies
        ]

        return {
            "success": True,
            "data": {
                "anomalies": anomalies_dict,
                "total_count": len(anomalies_dict),
                "start_date": start_date,
                "end_date": end_date,
                "detection_time": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving date range anomalies: {str(e)}")

@router.get("/by-location/{location}")
async def get_anomalies_by_location(
    location: str,
    db: Session = Depends(get_db)
):
    """Get anomalies for a specific location from the cache"""
    try:
        query = db.query(Anomaly).filter(Anomaly.location == location)
        location_anomalies = query.all()
        
        anomalies_dict = [
            {
                "id": a.id,
                "type": a.type,
                "location": a.location,
                "severity": a.severity,
                "timestamp": a.timestamp.isoformat(),
                "description": a.description,
                "details": a.details,
                "recommended_actions": a.recommended_actions
            } for a in location_anomalies
        ]

        return {
            "success": True,
            "data": {
                "location": location,
                "anomalies": anomalies_dict,
                "count": len(anomalies_dict),
                "time_range": "Entire dataset"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving location anomalies: {str(e)}")

@router.get("/by-severity/{severity}")
async def get_anomalies_by_severity(
    severity: str,
    db: Session = Depends(get_db)
):
    """Get anomalies filtered by severity level from the cache"""
    try:
        if severity not in ['low', 'medium', 'high', 'critical']:
            raise HTTPException(status_code=400, detail="Severity must be one of: low, medium, high, critical")
        
        query = db.query(Anomaly).filter(Anomaly.severity == severity)
        severity_anomalies = query.all()
        
        anomalies_dict = [
            {
                "id": a.id,
                "type": a.type,
                "location": a.location,
                "severity": a.severity,
                "timestamp": a.timestamp.isoformat(),
                "description": a.description,
                "details": a.details,
                "recommended_actions": a.recommended_actions
            } for a in severity_anomalies
        ]

        return {
            "success": True,
            "data": {
                "severity": severity,
                "anomalies": anomalies_dict,
                "count": len(anomalies_dict),
                "time_range": "Entire dataset"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving severity anomalies: {str(e)}")

@router.get("/types")
async def get_anomaly_types(db: Session = Depends(get_db)):
    """Get list of all anomaly types from the cache"""
    try:
        query = db.query(Anomaly.type).distinct()
        types = [row[0] for row in query.all()]
        
        return {
            "success": True,
            "data": {
                "anomaly_types": types,
                "descriptions": {
                    "overcrowding": "Number of people exceeds zone capacity",
                    "unauthorized_access": "Access without proper authorization",
                    "equipment_misuse": "Equipment used without booking",
                    "security_anomaly": "Suspicious movement patterns",
                    "security_drift": "Same person in multiple locations quickly",
                    "queue_congestion": "High transaction density",
                    "data_integrity_anomaly": "Missing or corrupted data"
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving anomaly types: {str(e)}")

@router.get("/summary")
async def get_anomaly_summary(
    db: Session = Depends(get_db)
):
    """Get summary of anomalies by type and severity from the cache"""
    try:
        query = db.query(Anomaly)
        anomalies = query.all()
        
        summary = {
            'total_anomalies': len(anomalies),
            'by_severity': {
                'critical': 0, 'high': 0, 'medium': 0, 'low': 0
            },
            'by_type': {},
            'by_location': {},
            'generated_at': datetime.now().isoformat(),
        }

        for anomaly in anomalies:
            summary['by_severity'][anomaly.severity] = summary['by_severity'].get(anomaly.severity, 0) + 1
            summary['by_type'][anomaly.type] = summary['by_type'].get(anomaly.type, 0) + 1
            summary['by_location'][anomaly.location] = summary['by_location'].get(anomaly.location, 0) + 1

        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")



import asyncio

# Variable to track caching status

caching_in_progress = False



@router.post("/cache-anomalies")

async def trigger_cache_anomalies():

    """Endpoint to trigger the anomaly caching process in the background."""

    global caching_in_progress

    if caching_in_progress:

        raise HTTPException(status_code=409, detail="Anomaly caching is already in progress.")



    async def run_caching():

        global caching_in_progress

        caching_in_progress = True

        try:

            from cache_anomalies import cache_anomalies

            await cache_anomalies()

        except Exception as e:

            print(f"Error during caching: {e}")

        finally:

            caching_in_progress = False



    asyncio.create_task(run_caching())

    return {"success": True, "message": "Anomaly caching process started in the background."}




@router.get("/by-entity/{entity_id}")
async def get_anomalies_by_entity(
    entity_id: str,
    db: Session = Depends(get_db)
):
    """Get all anomalies for a specific entity from the cache"""
    try:
        # Although anomalies are cached, we might still want the latest entity profile from Neo4j
        from services.entity_anomaly_detection import EntityAnomalyDetectionService
        neo4j_uri = settings.NEO4J_URI
        neo4j_user = settings.NEO4J_USER
        neo4j_password = settings.NEO4J_PASSWORD
        entity_service = EntityAnomalyDetectionService(neo4j_uri, neo4j_user, neo4j_password)
        entity_profile = entity_service.get_entity_profile(entity_id)
        if not entity_profile:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

        query = db.query(Anomaly).filter(Anomaly.entity_id == entity_id)
        entity_anomalies = query.all()

        anomalies_dict = [
            {
                "id": a.id,
                "type": a.type,
                "location": a.location,
                "severity": a.severity,
                "timestamp": a.timestamp.isoformat(),
                "description": a.description,
                "details": a.details,
                "recommended_actions": a.recommended_actions,
                "entity_id": a.entity_id
            } for a in entity_anomalies
        ]

        return {
            "success": True,
            "data": {
                "entity": entity_profile,
                "anomalies": anomalies_dict,
                "total_count": len(anomalies_dict),
                "time_range": "Entire dataset",
                "detection_time": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving entity anomalies: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check for anomaly detection service"""
    return {
        "success": True,
        "message": "Anomaly detection service is healthy",
        "timestamp": datetime.now().isoformat()
    }
