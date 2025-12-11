# backend/app/services/anomaly_detection_fixed.py
from neo4j import GraphDatabase
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class AnomalyType(Enum):
    OVERCROWDING = "overcrowding"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    EQUIPMENT_MISUSE = "equipment_misuse"
    SECURITY_ANOMALY = "security_anomaly"
    UNDERUTILIZATION = "underutilization"
    QUEUE_CONGESTION = "queue_congestion"
    DATA_INTEGRITY_ANOMALY = "data_integrity_anomaly"
    ENTRY_WITHOUT_EXIT = "entry_without_exit"
    EXIT_WITHOUT_ENTRY = "exit_without_entry"
    ABNORMAL_DWELL_TIME = "abnormal_dwell_time"
    CONSECUTIVE_SAME_DIRECTION = "consecutive_same_direction"
    NEGATIVE_OCCUPANCY = "negative_occupancy"

class SeverityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AnomalyDetectionService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        
        # Zone capacity definitions
        self.zone_capacities = {
            "LAB_101": 40,  # Updated to match your zone data
            "LAB_306": 30,  # Updated to match your zone data
            "LIB_ENT": 20,
            "AUDITORIUM": 300,
            "ADMIN_LOBBY": 50,
            "GYM": 80,
            "CAF_01": 200,
            "HOSTEL_GATE": 25
        }

    def get_dataset_time_range(self) -> Dict:
        """Get the full time range of available data - FIXED"""
        with self.driver.session() as session:
            # Only check SpatialActivity since Activity nodes don't exist
            result = session.run("""
                MATCH (sa:SpatialActivity)
                WHERE sa.timestamp IS NOT NULL
                RETURN min(sa.timestamp) as earliest_data,
                       max(sa.timestamp) as latest_data,
                       count(sa) as total_activities
            """)
            
            record = result.single()
            if record and record['earliest_data']:
                earliest = record['earliest_data']
                latest = record['latest_data']
                total = record['total_activities']
                
                # Calculate days difference properly
                if hasattr(earliest, 'to_native') and hasattr(latest, 'to_native'):
                    earliest_native = earliest.to_native()
                    latest_native = latest.to_native()
                    days_diff = (latest_native - earliest_native).days
                else:
                    # Fallback calculation
                    days_diff = 30  # Default span
                
                return {
                    'earliest_timestamp': earliest,
                    'latest_timestamp': latest,
                    'total_activities': total,
                    'dataset_span_days': days_diff
                }
            else:
                return {
                    'earliest_timestamp': None,
                    'latest_timestamp': None,
                    'total_activities': 0,
                    'dataset_span_days': 0
                }

    def detect_all_anomalies(self, time_window_hours: Optional[int] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           include_entity_anomalies: bool = True) -> List[Dict]:
        """Detect anomalies - SIMPLIFIED for current data structure"""
        anomalies = []

        # Determine time range, ensuring all datetimes are timezone-aware (UTC)
        if start_date and end_date:
            start_time = datetime.fromisoformat(f"{start_date}T00:00:00").replace(tzinfo=timezone.utc)
            end_time = datetime.fromisoformat(f"{end_date}T23:59:59").replace(tzinfo=timezone.utc)
        elif time_window_hours:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=time_window_hours)
        else:
            # Use entire dataset
            dataset_range = self.get_dataset_time_range()
            if dataset_range['earliest_timestamp'] and dataset_range['latest_timestamp']:
                start_time = dataset_range['earliest_timestamp']
                end_time = dataset_range['latest_timestamp']
                # Convert Neo4j DateTime to Python datetime if needed
                if hasattr(start_time, 'to_native'):
                    start_time = start_time.to_native()
                if hasattr(end_time, 'to_native'):
                    end_time = end_time.to_native()
                # Ensure they are aware
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
            else:
                # Fallback to last 30 days
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=30)

        try:
            logger.info(f"Detecting anomalies from {start_time} to {end_time}")

            # Detect overcrowding (works with SpatialActivity data)
            anomalies.extend(self._detect_overcrowding_simplified(start_time, end_time))

            # Detect underutilization
            anomalies.extend(self._detect_underutilization_simplified(start_time, end_time))

            # Detect data integrity issues
            anomalies.extend(self._detect_data_integrity_anomalies_simplified(start_time, end_time))

            # Add entity-level anomalies if requested
            if include_entity_anomalies:
                try:
                    from services.entity_anomaly_detection import EntityAnomalyDetectionService
                    entity_service = EntityAnomalyDetectionService(
                        self.neo4j_uri, self.neo4j_user, self.neo4j_password
                    )
                    entity_anomalies = entity_service.detect_entity_anomalies(start_time, end_time)
                    anomalies.extend(entity_anomalies)
                    logger.info(f"Detected {len(entity_anomalies)} entity-level anomalies")
                except Exception as e:
                    logger.warning(f"Could not detect entity anomalies: {str(e)}")

            # Convert all timestamps to datetime objects before sorting
            for anomaly in anomalies:
                if isinstance(anomaly['timestamp'], str):
                    anomaly['timestamp'] = datetime.fromisoformat(anomaly['timestamp'].replace('Z', '+00:00'))

            # Sort by severity and timestamp
            anomalies.sort(key=lambda x: (
                x['severity'] == 'critical',
                x['severity'] == 'high',
                x['severity'] == 'medium',
                x['timestamp']
            ), reverse=True)

            logger.info(f"Detected {len(anomalies)} total anomalies")
            return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return []

    def _detect_overcrowding_simplified(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect overcrowding using SpatialActivity data with direction-aware entry counts"""
        anomalies = []

        with self.driver.session() as session:
            # Find periods where entry count exceeds capacity (using new direction-based data)
            result = session.run("""
                MATCH (z:Zone)<-[:OCCURRED_IN]-(sa:SpatialActivity)
                WHERE sa.timestamp >= datetime($start_time)
                AND sa.timestamp <= datetime($end_time)
                AND sa.entry_count > 0
                WITH z, sa,
                     sa.timestamp.year as year,
                     sa.timestamp.month as month,
                     sa.timestamp.day as day,
                     sa.hour as hour
                WHERE sa.entry_count > z.capacity
                RETURN z.zone_id as zone_id,
                       z.name as zone_name,
                       z.capacity as capacity,
                       year,
                       month,
                       day,
                       hour,
                       max(sa.entry_count) as max_entries,
                       max(sa.exit_count) as max_exits,
                       max(sa.net_flow) as max_net_flow,
                       avg(sa.entry_count) as avg_entries,
                       max(sa.unique_visitors) as max_unique_visitors,
                       count(sa) as incident_count
                ORDER BY max_entries DESC
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for record in result:
                max_entries = record['max_entries']
                capacity = record['capacity']
                severity = SeverityLevel.CRITICAL.value if max_entries > capacity * 1.5 else SeverityLevel.HIGH.value

                # Construct date string and timestamp from components
                date_str = f"{record['year']}-{record['month']:02d}-{record['day']:02d}"
                timestamp = datetime(record['year'], record['month'], record['day'], record['hour'], 0, tzinfo=timezone.utc)

                anomalies.append({
                    'id': f"overcrowding_{record['zone_id']}_{date_str}_{record['hour']}",
                    'type': AnomalyType.OVERCROWDING.value,
                    'location': record['zone_id'],
                    'severity': severity,
                    'timestamp': timestamp,
                    'description': f"Overcrowding in {record['zone_name']}: {max_entries} entries (capacity: {capacity})",
                    'details': {
                        'zone_name': record['zone_name'],
                        'max_entries': max_entries,
                        'max_exits': record['max_exits'],
                        'net_flow': record['max_net_flow'],
                        'avg_entries': round(record['avg_entries'], 1),
                        'unique_visitors': record['max_unique_visitors'],
                        'capacity': capacity,
                        'occupancy_rate': round((max_entries / capacity) * 100, 1),
                        'incident_count': record['incident_count'],
                        'date': date_str,
                        'hour': record['hour']
                    },
                    'recommended_actions': [
                        "Implement capacity management",
                        "Deploy crowd control measures",
                        "Send real-time alerts to administrators",
                        "Monitor exit patterns to manage flow"
                    ]
                })

        return anomalies

    def _detect_underutilization_simplified(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect underutilized spaces"""
        anomalies = []
        
        with self.driver.session() as session:
            # Find zones with consistently low occupancy during peak hours
            result = session.run("""
                MATCH (z:Zone)<-[:OCCURRED_IN]-(sa:SpatialActivity)
                WHERE sa.timestamp >= datetime($start_time) 
                AND sa.timestamp <= datetime($end_time)
                AND sa.hour IN [9, 10, 11, 14, 15, 16, 17]  // Peak hours
                AND NOT sa.is_weekend
                WITH z, 
                     avg(sa.occupancy) as avg_occupancy,
                     max(sa.occupancy) as max_occupancy,
                     count(sa) as data_points
                WHERE avg_occupancy < (z.capacity * 0.2)  // Less than 20% capacity
                AND data_points > 5  // Ensure we have enough data
                RETURN z.zone_id as zone_id,
                       z.name as zone_name,
                       z.capacity as capacity,
                       avg_occupancy,
                       max_occupancy,
                       data_points
                ORDER BY avg_occupancy ASC
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })
            
            for record in result:
                utilization_rate = (record['avg_occupancy'] / record['capacity']) * 100
                
                anomalies.append({
                    'id': f"underutilization_{record['zone_id']}_{start_time.date()}",
                    'type': AnomalyType.UNDERUTILIZATION.value,
                    'location': record['zone_id'],
                    'severity': SeverityLevel.LOW.value if utilization_rate > 10 else SeverityLevel.MEDIUM.value,
                    'timestamp': start_time,
                    'description': f"Underutilization in {record['zone_name']}: {utilization_rate:.1f}% average occupancy during peak hours",
                    'details': {
                        'zone_name': record['zone_name'],
                        'avg_occupancy': round(record['avg_occupancy'], 1),
                        'max_occupancy': record['max_occupancy'],
                        'capacity': record['capacity'],
                        'utilization_rate': round(utilization_rate, 1),
                        'data_points': record['data_points']
                    },
                    'recommended_actions': [
                        "Review space allocation strategy",
                        "Consider repurposing underused areas",
                        "Analyze scheduling patterns"
                    ]
                })
        
        return anomalies

    def _detect_data_integrity_anomalies_simplified(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect data integrity issues including direction-based anomalies"""
        anomalies = []

        with self.driver.session() as session:
            # Check for missing timestamps
            null_timestamps = session.run("""
                MATCH (sa:SpatialActivity)
                WHERE sa.timestamp >= datetime($start_time)
                AND sa.timestamp <= datetime($end_time)
                AND sa.timestamp IS NULL
                RETURN count(sa) as null_count
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }).single()['null_count']

            if null_timestamps > 0:
                anomalies.append({
                    'id': f"data_integrity_null_timestamps_{start_time.date()}",
                    'type': AnomalyType.DATA_INTEGRITY_ANOMALY.value,
                    'location': 'SYSTEM_WIDE',
                    'severity': SeverityLevel.MEDIUM.value,
                    'timestamp': start_time,
                    'description': f"Data integrity issue: {null_timestamps} spatial activities with missing timestamps",
                    'details': {
                        'null_timestamp_count': null_timestamps,
                        'check_period': f"{start_time.date()} to {end_time.date()}"
                    },
                    'recommended_actions': [
                        "Review data collection processes",
                        "Check database constraints",
                        "Investigate data source reliability"
                    ]
                })

            # Check for negative net flow (more exits than entries - possible tailgating or data issue)
            negative_flow = session.run("""
                MATCH (z:Zone)<-[:OCCURRED_IN]-(sa:SpatialActivity)
                WHERE sa.timestamp >= datetime($start_time)
                AND sa.timestamp <= datetime($end_time)
                AND sa.net_flow IS NOT NULL
                AND sa.net_flow < -5
                RETURN z.zone_id as zone_id,
                       z.name as zone_name,
                       sa.timestamp as timestamp,
                       sa.hour as hour,
                       sa.entry_count as entries,
                       sa.exit_count as exits,
                       sa.net_flow as net_flow,
                       date(sa.timestamp) as date
                ORDER BY sa.net_flow ASC
                LIMIT 20
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for record in negative_flow:
                date_str = str(record['date'])
                timestamp = record['timestamp']
                if hasattr(timestamp, 'to_native'):
                    timestamp = timestamp.to_native()
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)

                anomalies.append({
                    'id': f"negative_flow_{record['zone_id']}_{date_str}_{record['hour']}",
                    'type': AnomalyType.NEGATIVE_OCCUPANCY.value,
                    'location': record['zone_id'],
                    'severity': SeverityLevel.HIGH.value,
                    'timestamp': timestamp,
                    'description': f"Negative occupancy flow in {record['zone_name']}: {record['exits']} exits vs {record['entries']} entries (net: {record['net_flow']})",
                    'details': {
                        'zone_name': record['zone_name'],
                        'entry_count': record['entries'],
                        'exit_count': record['exits'],
                        'net_flow': record['net_flow'],
                        'date': date_str,
                        'hour': record['hour'],
                        'anomaly_reason': 'More people exiting than entered - indicates tailgating on entry or data issue'
                    },
                    'recommended_actions': [
                        "Review CCTV footage for tailgating/piggybacking on entry",
                        "Check card reader hardware at entry points",
                        "Audit IN swipe compliance at entry gates",
                        "Consider turnstile or mantrap installation"
                    ]
                })

            # Check for legacy negative occupancy values
            negative_occupancy = session.run("""
                MATCH (sa:SpatialActivity)
                WHERE sa.timestamp >= datetime($start_time)
                AND sa.timestamp <= datetime($end_time)
                AND sa.occupancy < 0
                RETURN count(sa) as negative_count, collect(DISTINCT sa.zone_id) as affected_zones
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }).single()

            if negative_occupancy['negative_count'] > 0:
                anomalies.append({
                    'id': f"data_integrity_negative_occupancy_{start_time.date()}",
                    'type': AnomalyType.DATA_INTEGRITY_ANOMALY.value,
                    'location': 'SYSTEM_WIDE',
                    'severity': SeverityLevel.HIGH.value,
                    'timestamp': start_time,
                    'description': f"Data integrity issue: {negative_occupancy['negative_count']} records with negative occupancy",
                    'details': {
                        'negative_count': negative_occupancy['negative_count'],
                        'affected_zones': negative_occupancy['affected_zones'],
                        'check_period': f"{start_time.date()} to {end_time.date()}"
                    },
                    'recommended_actions': [
                        "Fix data validation rules",
                        "Correct negative occupancy values",
                        "Review sensor calibration"
                    ]
                })

        return anomalies

    def get_all_historical_anomalies(self) -> List[Dict]:
        """Get all anomalies from the entire dataset"""
        return self.detect_all_anomalies(time_window_hours=None)

    def get_anomalies_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get anomalies within a specific date range"""
        return self.detect_all_anomalies(start_date=start_date, end_date=end_date)

    def get_anomaly_summary(self, time_window_hours: Optional[int] = None, 
                          start_date: Optional[str] = None, 
                          end_date: Optional[str] = None) -> Dict:
        """Get summary of anomalies by type and severity"""
        anomalies = self.detect_all_anomalies(time_window_hours, start_date, end_date)
        
        # Determine actual time range used
        if start_date and end_date:
            time_range_description = f"From {start_date} to {end_date}"
        elif time_window_hours:
            time_range_description = f"Last {time_window_hours} hours"
        else:
            dataset_range = self.get_dataset_time_range()
            if dataset_range['earliest_timestamp'] and dataset_range['latest_timestamp']:
                earliest = dataset_range['earliest_timestamp']
                latest = dataset_range['latest_timestamp']
                # Handle Neo4j DateTime objects
                if hasattr(earliest, 'to_native'):
                    earliest = earliest.to_native()
                if hasattr(latest, 'to_native'):
                    latest = latest.to_native()
                earliest_str = earliest.strftime("%Y-%m-%d")
                latest_str = latest.strftime("%Y-%m-%d")
                time_range_description = f"Entire dataset ({earliest_str} to {latest_str})"
            else:
                time_range_description = "No data available"
        
        summary = {
            'total_anomalies': len(anomalies),
            'time_range': time_range_description,
            'by_severity': {
                'critical': len([a for a in anomalies if a['severity'] == 'critical']),
                'high': len([a for a in anomalies if a['severity'] == 'high']),
                'medium': len([a for a in anomalies if a['severity'] == 'medium']),
                'low': len([a for a in anomalies if a['severity'] == 'low'])
            },
            'by_type': {},
            'by_location': {},
            'recent_anomalies': anomalies[:5],  # Most recent 5
            'generated_at': datetime.now().isoformat(),
            'dataset_info': self.get_dataset_time_range()
        }
        
        # Count by type
        for anomaly in anomalies:
            anomaly_type = anomaly['type']
            location = anomaly['location']
            
            summary['by_type'][anomaly_type] = summary['by_type'].get(anomaly_type, 0) + 1
            summary['by_location'][location] = summary['by_location'].get(location, 0) + 1
        
        return summary

    def get_anomaly_trends(self, granularity: str = "daily") -> Dict:
        """Get anomaly trends over time"""
        all_anomalies = self.get_all_historical_anomalies()
        
        trends = {
            'by_date': {},
            'by_type_over_time': {},
            'by_severity_over_time': {},
            'peak_periods': [],
            'total_count': len(all_anomalies),
            'granularity': granularity
        }
        
        for anomaly in all_anomalies:
            # Parse timestamp
            timestamp = anomaly['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Group by date based on granularity
            if granularity == "daily":
                date_key = timestamp.strftime("%Y-%m-%d")
            elif granularity == "weekly":
                week_start = timestamp - timedelta(days=timestamp.weekday())
                date_key = week_start.strftime("%Y-%m-%d")
            elif granularity == "monthly":
                date_key = timestamp.strftime("%Y-%m")
            else:
                date_key = timestamp.strftime("%Y-%m-%d")
            
            # Count by date
            trends['by_date'][date_key] = trends['by_date'].get(date_key, 0) + 1
            
            # Count by type over time
            anomaly_type = anomaly['type']
            if anomaly_type not in trends['by_type_over_time']:
                trends['by_type_over_time'][anomaly_type] = {}
            trends['by_type_over_time'][anomaly_type][date_key] = trends['by_type_over_time'][anomaly_type].get(date_key, 0) + 1
            
            # Count by severity over time
            severity = anomaly['severity']
            if severity not in trends['by_severity_over_time']:
                trends['by_severity_over_time'][severity] = {}
            trends['by_severity_over_time'][severity][date_key] = trends['by_severity_over_time'][severity].get(date_key, 0) + 1
        
        # Find peak periods (top 5 dates with most anomalies)
        sorted_dates = sorted(trends['by_date'].items(), key=lambda x: x[1], reverse=True)
        trends['peak_periods'] = [
            {'date': date, 'anomaly_count': count} 
            for date, count in sorted_dates[:5]
        ]
        
        return trends