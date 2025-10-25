# backend/app/api/spatial_routes.py
from config import settings
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta
from services.spatial_forecasting import SpatialForecastingService
import os

router = APIRouter(prefix="/api/v1/spatial", tags=["spatial-forecasting"])

# Dependency to get spatial service
def get_spatial_service():
    neo4j_uri = settings.NEO4J_URI
    neo4j_user = settings.NEO4J_USER
    neo4j_password = settings.NEO4J_PASSWORD

    return SpatialForecastingService(neo4j_uri, neo4j_user, neo4j_password)

@router.get("/zones")
async def get_all_zones(spatial_service: SpatialForecastingService = Depends(get_spatial_service)):
    """Get list of all zones"""
    try:
        zones = spatial_service.get_all_zones()
        return {
            "success": True,
            "data": zones,
            "count": len(zones)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving zones: {str(e)}")

@router.get("/zones/{zone_id}")
async def get_zone_details(
    zone_id: str, 
    spatial_service: SpatialForecastingService = Depends(get_spatial_service)
):
    """Get detailed information about a specific zone"""
    try:
        zone = spatial_service.get_zone_details(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")
        
        return {
            "success": True,
            "data": zone
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving zone details: {str(e)}")

@router.get("/zones/{zone_id}/occupancy")
async def get_current_occupancy(
    zone_id: str,
    spatial_service: SpatialForecastingService = Depends(get_spatial_service)
):
    """Get current occupancy for a zone"""
    try:
        occupancy = spatial_service.get_current_occupancy(zone_id)
        if not occupancy:
            raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")
        
        return {
            "success": True,
            "data": occupancy
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving occupancy: {str(e)}")

@router.get("/zones/{zone_id}/history")
async def get_zone_history(
    zone_id: str,
    days_back: int = Query(7, ge=1, le=300, description="Number of days to look back"),
    spatial_service: SpatialForecastingService = Depends(get_spatial_service)
):
    """Get historical occupancy data for a zone"""
    try:
        history = spatial_service.get_historical_occupancy(zone_id, days_back)
        return {
            "success": True,
            "data": history,
            "period_days": days_back,
            "data_points": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@router.get("/zones/{zone_id}/forecast")
async def get_zone_forecast(
    zone_id: str,
    hours_ahead: int = Query(24, ge=1, le=168, description="Hours to forecast ahead"),
    spatial_service: SpatialForecastingService = Depends(get_spatial_service)
):
    """Get occupancy forecast for a zone"""
    try:
        forecasts = []
        current_time = datetime.now()
        
        for hour in range(1, hours_ahead + 1):
            target_time = current_time + timedelta(hours=hour)
            forecast = spatial_service.predict_zone_occupancy(zone_id, target_time)
            forecasts.append(forecast)
        
        return {
            "success": True,
            "data": {
                "zone_id": zone_id,
                "forecasts": forecasts,
                "generated_at": current_time.isoformat(),
                "forecast_period_hours": hours_ahead
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating forecast: {str(e)}")

@router.get("/zones/{zone_id}/connections")
async def get_zone_connections(
    zone_id: str,
    spatial_service: SpatialForecastingService = Depends(get_spatial_service)
):
    """Get zones connected to the specified zone"""
    try:
        connections = spatial_service.get_zone_connections(zone_id)
        return {
            "success": True,
            "data": {
                "zone_id": zone_id,
                "connections": connections,
                "connection_count": len(connections)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving connections: {str(e)}")

@router.get("/campus/summary")
async def get_campus_summary(spatial_service: SpatialForecastingService = Depends(get_spatial_service)):
    """Get overall campus activity summary"""
    try:
        summary = spatial_service.get_campus_summary()
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving campus summary: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "success": True,
        "message": "Spatial forecasting API is healthy",
        "timestamp": datetime.now().isoformat()
    }