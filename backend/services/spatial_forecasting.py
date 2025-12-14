# backend/app/services/spatial_forecasting.py
from neo4j import GraphDatabase
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

class SpatialForecastingService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.occupancy_models = {}
        self.scaler = StandardScaler()
    
    def get_all_zones(self) -> List[Dict]:
        """Get all zones with their basic info"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (z:Zone)
                RETURN z.zone_id as zone_id,
                       z.name as name,
                       z.zone_type as zone_type,
                       z.capacity as capacity,
                       z.building as building,
                       z.floor as floor,
                       z.latitude as latitude,
                       z.longitude as longitude,
                       z.department as department
                ORDER BY z.zone_id
            """)
            
            return [dict(record) for record in result]
    
    def get_zone_details(self, zone_id: str) -> Optional[Dict]:
        """Get detailed information about a specific zone"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (z:Zone {zone_id: $zone_id})
                RETURN z.zone_id as zone_id,
                       z.name as name,
                       z.zone_type as zone_type,
                       z.capacity as capacity,
                       z.building as building,
                       z.floor as floor,
                       z.latitude as latitude,
                       z.longitude as longitude,
                       z.description as description,
                       z.operating_start as operating_start,
                       z.operating_end as operating_end,
                       z.access_level as access_level,
                       z.facilities as facilities,
                       z.peak_hours as peak_hours,
                       z.department as department,
                       z.zone_category as zone_category
            """, zone_id=zone_id)
            
            record = result.single()
            return dict(record) if record else None
    
    def get_current_occupancy(self, zone_id: str) -> Dict:
        """Get current occupancy for a zone based on recent activities"""
        with self.driver.session() as session:
            # Get recent synthetic activities (last 2 hours)
            # Note: We use localdatetime() since simulator creates timestamps without timezone
            # and we compare against local time window
            now = datetime.now()
            two_hours_ago = now - timedelta(hours=2)

            result = session.run("""
                MATCH (z:Zone {zone_id: $zone_id})<-[:OCCURRED_IN]-(sa:SpatialActivity)
                WHERE sa.timestamp >= datetime($cutoff_time)
                WITH z, sa
                ORDER BY sa.timestamp DESC
                LIMIT 1
                RETURN z.zone_id as zone_id,
                       z.name as zone_name,
                       z.capacity as capacity,
                       sa.occupancy as current_occupancy,
                       sa.timestamp as last_updated
            """, zone_id=zone_id, cutoff_time=two_hours_ago.isoformat())
            
            record = result.single()
            if record:
                occupancy = record["current_occupancy"]
                capacity = record["capacity"]
                occupancy_rate = (occupancy / capacity * 100) if capacity > 0 else 0
                
                return {
                    "zone_id": record["zone_id"],
                    "zone_name": record["zone_name"],
                    "current_occupancy": occupancy,
                    "capacity": capacity,
                    "occupancy_rate": round(occupancy_rate, 2),
                    "last_updated": record["last_updated"],
                    "status": self._get_occupancy_status(occupancy_rate)
                }
            else:
                # No recent data, return empty
                zone_info = self.get_zone_details(zone_id)
                if zone_info:
                    return {
                        "zone_id": zone_id,
                        "zone_name": zone_info["name"],
                        "current_occupancy": 0,
                        "capacity": zone_info["capacity"],
                        "occupancy_rate": 0,
                        "last_updated": None,
                        "status": "unknown"
                    }
                return None
    
    def _get_occupancy_status(self, occupancy_rate: float) -> str:
        """Determine occupancy status based on rate"""
        if occupancy_rate >= 90:
            return "critical"
        elif occupancy_rate >= 75:
            return "high"
        elif occupancy_rate >= 50:
            return "moderate"
        elif occupancy_rate >= 25:
            return "low"
        else:
            return "minimal"
    
    def get_historical_occupancy(self, zone_id: str, days_back: int = 7) -> List[Dict]:
        """Get historical occupancy data for a zone"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (z:Zone {zone_id: $zone_id})<-[:OCCURRED_IN]-(sa:SpatialActivity)
                WHERE sa.timestamp >= datetime() - duration({days: $days_back})
                WITH sa, date(sa.timestamp) as activity_date, sa.hour as hour
                RETURN activity_date,
                       hour,
                       avg(sa.occupancy) as avg_occupancy,
                       max(sa.occupancy) as max_occupancy,
                       min(sa.occupancy) as min_occupancy,
                       count(sa) as data_points
                ORDER BY activity_date, hour
            """, zone_id=zone_id, days_back=days_back)
            
            return [dict(record) for record in result]
    
    def predict_zone_occupancy(self, zone_id: str, target_datetime: datetime) -> Dict:
        """Simple occupancy prediction based on historical patterns"""
        with self.driver.session() as session:
            # Get historical data for similar time periods
            target_hour = target_datetime.hour
            target_day_of_week = target_datetime.weekday() + 1
            is_weekend = target_datetime.weekday() >= 5
            
            result = session.run("""
                MATCH (z:Zone {zone_id: $zone_id})<-[:OCCURRED_IN]-(sa:SpatialActivity)
                WHERE sa.hour = $target_hour
                AND sa.day_of_week = $target_day_of_week
                RETURN avg(sa.occupancy) as avg_occupancy,
                       count(sa) as data_points
            """, zone_id=zone_id, target_hour=target_hour, target_day_of_week=target_day_of_week)
            
            record = result.single()
            
            if record and record["data_points"] > 0:
                predicted_occupancy = max(0, int(record["avg_occupancy"]))
                confidence = min(0.95, record["data_points"] / 30.0)  # More data = higher confidence
                
                reasoning = f"Based on {record['data_points']} similar time periods. "
                reasoning += f"Historical average: {record['avg_occupancy']:.1f}. "
                
                if is_weekend:
                    reasoning += "Weekend pattern applied."
                else:
                    reasoning += "Weekday pattern applied."
                
                return {
                    "zone_id": zone_id,
                    "target_datetime": target_datetime.isoformat(),
                    "predicted_occupancy": predicted_occupancy,
                    "confidence": round(confidence, 2),
                    "reasoning": reasoning,
                    "data_points_used": record["data_points"]
                }
            else:
                return {
                    "zone_id": zone_id,
                    "target_datetime": target_datetime.isoformat(),
                    "predicted_occupancy": 0,
                    "confidence": 0.0,
                    "reasoning": "No historical data available for this time period",
                    "data_points_used": 0
                }
    
    def get_campus_summary(self) -> Dict:
        """Get overall campus activity summary"""
        now = datetime.now()
        two_hours_ago = now - timedelta(hours=2)

        with self.driver.session() as session:
            # Get current occupancy for all zones
            current_occupancy = session.run("""
                MATCH (z:Zone)
                OPTIONAL MATCH (z)<-[:OCCURRED_IN]-(sa:SpatialActivity)
                WHERE sa.timestamp >= datetime($cutoff_time)
                WITH z, sa
                ORDER BY sa.timestamp DESC
                WITH z, collect(sa)[0] as latest_activity
                RETURN z.zone_id as zone_id,
                       z.name as zone_name,
                       z.zone_type as zone_type,
                       z.capacity as capacity,
                       CASE WHEN latest_activity IS NOT NULL
                            THEN latest_activity.occupancy
                            ELSE 0 END as current_occupancy
                ORDER BY z.zone_id
            """, cutoff_time=two_hours_ago.isoformat()).data()
            
            # Calculate summary statistics
            total_capacity = sum(record["capacity"] for record in current_occupancy)
            total_occupancy = sum(record["current_occupancy"] for record in current_occupancy)
            overall_rate = (total_occupancy / total_capacity * 100) if total_capacity > 0 else 0
            
            # Find high-traffic zones
            high_traffic = [
                record for record in current_occupancy 
                if record["current_occupancy"] / record["capacity"] >= 0.75
            ]
            
            # Find underutilized zones
            underutilized = [
                record for record in current_occupancy 
                if record["current_occupancy"] / record["capacity"] <= 0.25
            ]
            
            return {
                "summary": {
                    "total_zones": len(current_occupancy),
                    "total_capacity": total_capacity,
                    "total_occupancy": total_occupancy,
                    "overall_occupancy_rate": round(overall_rate, 2),
                    "status": self._get_occupancy_status(overall_rate)
                },
                "zone_details": current_occupancy,
                "high_traffic_zones": high_traffic,
                "underutilized_zones": underutilized,
                "last_updated": datetime.now().isoformat()
            }
    
    def get_zone_connections(self, zone_id: str) -> List[Dict]:
        """Get zones connected to the specified zone"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (z1:Zone {zone_id: $zone_id})-[r:CONNECTED_TO]->(z2:Zone)
                RETURN z2.zone_id as connected_zone_id,
                       z2.name as connected_zone_name,
                       r.distance_meters as distance_meters,
                       r.walking_time_minutes as walking_time_minutes
                UNION
                MATCH (z1:Zone)-[r:CONNECTED_TO]->(z2:Zone {zone_id: $zone_id})
                RETURN z1.zone_id as connected_zone_id,
                       z1.name as connected_zone_name,
                       r.distance_meters as distance_meters,
                       r.walking_time_minutes as walking_time_minutes
            """, zone_id=zone_id)
            
            return [dict(record) for record in result]