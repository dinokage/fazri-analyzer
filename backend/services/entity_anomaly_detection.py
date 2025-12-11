"""
Entity-Level Anomaly Detection Service
Detects anomalies based on individual entity behavior
"""

from neo4j import GraphDatabase
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import hashlib

logger = logging.getLogger(__name__)

def serialize_neo4j_datetime(dt):
    """Convert Neo4j datetime to ISO string"""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if hasattr(dt, 'to_native'):
        # Neo4j datetime object
        return dt.to_native().isoformat()
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)

def generate_unique_id(anomaly_type: str, entity_id: str, location: str, timestamp: str, extra: str = "") -> str:
    """Generate a unique ID for an anomaly using hash"""
    # Combine all fields to ensure uniqueness
    unique_string = f"{anomaly_type}_{entity_id}_{location}_{timestamp}_{extra}"
    # Create a short hash
    hash_obj = hashlib.md5(unique_string.encode())
    short_hash = hash_obj.hexdigest()[:12]
    return f"{anomaly_type}_{entity_id}_{short_hash}"

class EntityAnomalyDetectionService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

        # Zone access restrictions
        self.restricted_zones = {
            'LAB_305': ['ECE', 'EEE', 'Physics'],  # Department restricted
            'ROOM_A1': ['faculty', 'staff'],       # Role restricted
            'ROOM_A2': ['faculty', 'staff'],       # Role restricted
            'HOSTEL_GATE': ['student']              # Students only
        }

        # Operating hours for zones
        self.zone_hours = {
            'LAB_101': (7, 21),
            'LAB_102': (8, 20),
            'LAB_305': (8, 19),  # Strict hours
            'ADMIN_LOBBY': (8, 18),
            'LIB_ENT': (7, 23),
            'GYM': (5, 23),
            'CAF_01': (6, 23),
            'ROOM_A1': (8, 18),
            'ROOM_A2': (8, 18),
            'SEM_01': (8, 20),
            'AUDITORIUM': (8, 22),
            'HOSTEL_GATE': (0, 23)  # 24/7 but curfew at 23:00
        }

    def detect_entity_anomalies(self, start_time: datetime, end_time: datetime, entity_id: Optional[str] = None) -> List[Dict]:
        """Detect all entity-level anomalies, optionally filtered by entity_id"""
        anomalies = []

        try:
            # 1. Off-hours access violations
            anomalies.extend(self._detect_off_hours_access(start_time, end_time, entity_id))

            # 2. Role-based access violations
            anomalies.extend(self._detect_role_violations(start_time, end_time))

            # 3. Department-based access violations
            anomalies.extend(self._detect_department_violations(start_time, end_time))

            # 4. Impossible travel detection (updated with direction awareness)
            anomalies.extend(self._detect_impossible_travel(start_time, end_time))

            # 5. Multi-modal location mismatches
            anomalies.extend(self._detect_location_mismatches(start_time, end_time))

            # 6. Post-curfew hostel entries (updated with direction)
            anomalies.extend(self._detect_curfew_violations(start_time, end_time))

            # 7. Excessive access frequency
            anomalies.extend(self._detect_excessive_access(start_time, end_time))

            # 8. Booking no-shows
            anomalies.extend(self._detect_booking_anomalies(start_time, end_time))

            # 9. Entry without exit (tailgating/piggybacking detection)
            anomalies.extend(self._detect_entry_without_exit(start_time, end_time))

            # 10. Exit without entry (suspicious exit)
            anomalies.extend(self._detect_exit_without_entry(start_time, end_time))

            # 11. Abnormal dwell time (person in zone too long)
            anomalies.extend(self._detect_abnormal_dwell_time(start_time, end_time))

            # 12. Consecutive same-direction swipes (possible card sharing)
            anomalies.extend(self._detect_consecutive_same_direction(start_time, end_time))

            # Filter by entity_id if specified
            if entity_id:
                anomalies = [a for a in anomalies if a.get('entity_id') == entity_id]

            return sorted(anomalies, key=lambda x: x['timestamp'], reverse=True)

        except Exception as e:
            logger.error(f"Error detecting entity anomalies: {str(e)}")
            return []

    def get_entity_profile(self, entity_id: str) -> Optional[Dict]:
        """Get basic profile information for an entity"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Entity {entity_id: $entity_id})
                RETURN e.entity_id as entity_id,
                       e.name as name,
                       e.role as role,
                       e.department as department,
                       e.card_id as card_id
            """, {'entity_id': entity_id})

            record = result.single()
            if record:
                return dict(record)
            return None

    def _detect_off_hours_access(self, start_time: datetime, end_time: datetime, entity_id: Optional[str] = None) -> List[Dict]:
        """Detect access outside operating hours"""
        anomalies = []

        with self.driver.session() as session:
            # Build query with optional entity_id filter
            entity_filter = "AND e.entity_id = $entity_id" if entity_id else ""

            query = f"""
                MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone)
                WHERE r.timestamp >= datetime($start_time)
                AND r.timestamp <= datetime($end_time)
                AND z.zone_id IN $monitored_zones
                {entity_filter}
                WITH e, r, z,
                     r.timestamp.hour as access_hour
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       z.zone_id as zone_id,
                       z.name as zone_name,
                       r.timestamp as timestamp,
                       access_hour,
                       z.zone_id as zone_key
                ORDER BY r.timestamp DESC
            """

            params = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'monitored_zones': list(self.zone_hours.keys())
            }
            if entity_id:
                params['entity_id'] = entity_id

            result = session.run(query, params)

            for rec in result:
                zone_key = rec['zone_key']
                if zone_key in self.zone_hours:
                    start_hour, end_hour = self.zone_hours[zone_key]
                    access_hour = rec['access_hour']

                    # Check if access is outside operating hours
                    if access_hour < start_hour or access_hour >= end_hour:
                        severity = 'critical' if zone_key in ['LAB_305', 'ROOM_A1', 'ROOM_A2'] else 'high'
                        timestamp_str = serialize_neo4j_datetime(rec['timestamp'])

                        anomalies.append({
                            'id': generate_unique_id('off_hours', rec['entity_id'], rec['zone_id'], timestamp_str, str(access_hour)),
                            'type': 'off_hours_access',
                            'severity': severity,
                            'entity_id': rec['entity_id'],
                            'entity_name': rec['entity_name'],
                            'entity_role': rec['role'],
                            'location': rec['zone_id'],
                            'location_name': rec['zone_name'],
                            'timestamp': timestamp_str,
                            'description': f"{rec['entity_name']} ({rec['role']}) accessed {rec['zone_name']} at {access_hour}:00 (outside operating hours {start_hour}:00-{end_hour}:00)",
                            'details': {
                                'access_hour': access_hour,
                                'operating_hours': f"{start_hour}:00-{end_hour}:00",
                                'hours_outside': min(access_hour - start_hour if access_hour < start_hour else access_hour - end_hour, 24)
                            },
                            'recommended_actions': [
                                "Review access authorization",
                                "Check if emergency access was needed",
                                "Investigate potential security breach" if severity == 'critical' else "Log for review"
                            ]
                        })

        return anomalies

    def _detect_role_violations(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect role-based access violations (e.g., students in faculty-only rooms)"""
        anomalies = []

        with self.driver.session() as session:
            # Check ROOM_A1 and ROOM_A2 (faculty/staff only)
            result = session.run("""
                MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone)
                WHERE r.timestamp >= datetime($start_time)
                AND r.timestamp <= datetime($end_time)
                AND z.zone_id IN ['ROOM_A1', 'ROOM_A2']
                AND e.role = 'student'
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       e.department as department,
                       z.zone_id as zone_id,
                       z.name as zone_name,
                       r.timestamp as timestamp,
                       count(*) as violation_count
                ORDER BY r.timestamp DESC
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                timestamp_str = serialize_neo4j_datetime(rec['timestamp'])
                anomalies.append({
                    'id': generate_unique_id('role_violation', rec['entity_id'], rec['zone_id'], timestamp_str),
                    'type': 'role_violation',
                    'severity': 'high',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'entity_role': rec['role'],
                    'location': rec['zone_id'],
                    'location_name': rec['zone_name'],
                    'timestamp': timestamp_str,
                    'description': f"Student {rec['entity_name']} accessed faculty-only room {rec['zone_name']} (requires faculty/staff authorization)",
                    'details': {
                        'entity_role': rec['role'],
                        'required_role': 'faculty or staff',
                        'department': rec['department'],
                        'violation_count': rec['violation_count']
                    },
                    'recommended_actions': [
                        "Verify if student had escort/permission",
                        "Check booking records",
                        "Update access control policies"
                    ]
                })

        return anomalies

    def _detect_department_violations(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect department-restricted zone access violations"""
        anomalies = []

        with self.driver.session() as session:
            # Check LAB_305 (ECE/EEE/Physics only)
            result = session.run("""
                MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone {zone_id: 'LAB_305'})
                WHERE r.timestamp >= datetime($start_time)
                AND r.timestamp <= datetime($end_time)
                AND NOT e.department IN $allowed_departments
                AND e.role = 'student'
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       e.department as department,
                       z.zone_id as zone_id,
                       z.name as zone_name,
                       r.timestamp as timestamp
                ORDER BY r.timestamp DESC
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'allowed_departments': ['ECE', 'EEE', 'Physics']
            })

            for rec in result:
                timestamp_str = serialize_neo4j_datetime(rec['timestamp'])
                anomalies.append({
                    'id': generate_unique_id('dept_violation', rec['entity_id'], rec['zone_id'], timestamp_str),
                    'type': 'department_violation',
                    'severity': 'high',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'entity_role': rec['role'],
                    'location': rec['zone_id'],
                    'location_name': rec['zone_name'],
                    'timestamp': timestamp_str,
                    'description': f"{rec['department']} student {rec['entity_name']} accessed ECE/EEE-restricted lab {rec['zone_name']}",
                    'details': {
                        'entity_department': rec['department'],
                        'allowed_departments': ['ECE', 'EEE', 'Physics'],
                        'zone_restrictions': 'Department-restricted equipment area'
                    },
                    'recommended_actions': [
                        "Verify if cross-department project access was authorized",
                        "Check faculty permission records",
                        "Review lab access policies"
                    ]
                })

        return anomalies

    def _detect_impossible_travel(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect impossible travel between zones (direction-aware: OUT from zone1 then IN to zone2)"""
        anomalies = []

        with self.driver.session() as session:
            # Find entity movements: OUT from one zone, then IN to another too quickly
            # This is more accurate than just checking any swipe
            result = session.run("""
                MATCH (e:Entity)-[r1:SWIPED_CARD {direction: 'OUT'}]->(z1:Zone)
                MATCH (e)-[r2:SWIPED_CARD {direction: 'IN'}]->(z2:Zone)
                WHERE r1.timestamp >= datetime($start_time)
                AND r1.timestamp <= datetime($end_time)
                AND r2.timestamp > r1.timestamp
                AND z1.zone_id <> z2.zone_id
                WITH e, z1, z2, r1, r2,
                     duration.between(r1.timestamp, r2.timestamp).seconds as time_diff_seconds
                WHERE time_diff_seconds < 120  // Less than 2 minutes between zones
                AND time_diff_seconds > 0
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       z1.zone_id as from_zone,
                       z1.name as from_zone_name,
                       z2.zone_id as to_zone,
                       z2.name as to_zone_name,
                       r1.timestamp as exit_timestamp,
                       r2.timestamp as entry_timestamp,
                       time_diff_seconds
                ORDER BY time_diff_seconds ASC
                LIMIT 50
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                timestamp_str = serialize_neo4j_datetime(rec['exit_timestamp'])
                location_str = f"{rec['from_zone']} → {rec['to_zone']}"
                anomalies.append({
                    'id': generate_unique_id('impossible_travel', rec['entity_id'], location_str, timestamp_str, str(rec['time_diff_seconds'])),
                    'type': 'impossible_travel',
                    'severity': 'critical',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'entity_role': rec['role'],
                    'location': location_str,
                    'timestamp': timestamp_str,
                    'description': f"{rec['entity_name']} exited {rec['from_zone_name']} and entered {rec['to_zone_name']} only {rec['time_diff_seconds']}s later (impossible travel)",
                    'details': {
                        'from_zone': rec['from_zone'],
                        'to_zone': rec['to_zone'],
                        'time_difference_seconds': rec['time_diff_seconds'],
                        'exit_time': serialize_neo4j_datetime(rec['exit_timestamp']),
                        'entry_time': serialize_neo4j_datetime(rec['entry_timestamp']),
                        'movement_pattern': 'OUT → IN'
                    },
                    'recommended_actions': [
                        "Investigate card sharing or cloning",
                        "Check for cloned access cards",
                        "Review CCTV footage at both locations",
                        "Possible identity fraud or buddy-swiping"
                    ]
                })

        return anomalies

    def _detect_location_mismatches(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect mismatches between card swipes and WiFi connections"""
        anomalies = []

        with self.driver.session() as session:
            # Find cases where card swipe location != WiFi location within 5 minutes
            result = session.run("""
                MATCH (e:Entity)-[card:SWIPED_CARD]->(z1:Zone)
                MATCH (e)-[wifi:CONNECTED_TO_WIFI]->(z2:Zone)
                WHERE card.timestamp >= datetime($start_time)
                AND card.timestamp <= datetime($end_time)
                AND abs(duration.between(card.timestamp, wifi.timestamp).minutes) <= 5
                AND z1.zone_id <> z2.zone_id
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       z1.zone_id as card_zone,
                       z1.name as card_zone_name,
                       z2.zone_id as wifi_zone,
                       z2.name as wifi_zone_name,
                       card.timestamp as card_time,
                       wifi.timestamp as wifi_time
                ORDER BY card.timestamp DESC
                LIMIT 20
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                timestamp_str = serialize_neo4j_datetime(rec['card_time'])
                anomalies.append({
                    'id': generate_unique_id('location_mismatch', rec['entity_id'], rec['card_zone'], timestamp_str, rec['wifi_zone']),
                    'type': 'location_mismatch',
                    'severity': 'medium',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'location': rec['card_zone'],
                    'timestamp': timestamp_str,
                    'description': f"{rec['entity_name']} card swipe at {rec['card_zone_name']} but WiFi connection at {rec['wifi_zone_name']} (multi-modal conflict)",
                    'details': {
                        'card_location': rec['card_zone'],
                        'wifi_location': rec['wifi_zone'],
                        'card_timestamp': serialize_neo4j_datetime(rec['card_time']),
                        'wifi_timestamp': serialize_neo4j_datetime(rec['wifi_time'])
                    },
                    'recommended_actions': [
                        "Check for tailgating (card lent to someone else)",
                        "Verify WiFi AP coverage overlap",
                        "Review CCTV to confirm actual location"
                    ]
                })

        return anomalies

    def _detect_curfew_violations(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect hostel entries after curfew (23:00) and late exits - direction aware"""
        anomalies = []

        with self.driver.session() as session:
            # Detect late entries (IN after curfew) - more serious
            result = session.run("""
                MATCH (e:Entity)-[r:SWIPED_CARD {direction: 'IN'}]->(z:Zone {zone_id: 'HOSTEL_GATE'})
                WHERE r.timestamp >= datetime($start_time)
                AND r.timestamp <= datetime($end_time)
                AND r.timestamp.hour >= 23
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       r.timestamp as timestamp,
                       r.timestamp.hour as hour,
                       r.timestamp.minute as minute,
                       'IN' as direction
                ORDER BY r.timestamp DESC
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                timestamp_str = serialize_neo4j_datetime(rec['timestamp'])
                anomalies.append({
                    'id': generate_unique_id('curfew_late_entry', rec['entity_id'], 'HOSTEL_GATE', timestamp_str, str(rec['hour'])),
                    'type': 'curfew_violation',
                    'severity': 'high',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'entity_role': rec['role'],
                    'location': 'HOSTEL_GATE',
                    'timestamp': timestamp_str,
                    'description': f"{rec['entity_name']} returned to hostel at {rec['hour']}:{rec['minute']:02d} (after 23:00 curfew)",
                    'details': {
                        'entry_hour': rec['hour'],
                        'entry_minute': rec['minute'],
                        'direction': 'IN',
                        'curfew_time': '23:00',
                        'violation_type': 'Late return to hostel'
                    },
                    'recommended_actions': [
                        "Log for disciplinary review",
                        "Check if emergency/valid reason documented",
                        "Pattern analysis for repeat offenders",
                        "Issue warning or penalty based on policy"
                    ]
                })

            # Detect late exits (OUT after curfew) - potentially more concerning
            result_exits = session.run("""
                MATCH (e:Entity)-[r:SWIPED_CARD {direction: 'OUT'}]->(z:Zone {zone_id: 'HOSTEL_GATE'})
                WHERE r.timestamp >= datetime($start_time)
                AND r.timestamp <= datetime($end_time)
                AND r.timestamp.hour >= 23
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       r.timestamp as timestamp,
                       r.timestamp.hour as hour,
                       r.timestamp.minute as minute,
                       'OUT' as direction
                ORDER BY r.timestamp DESC
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result_exits:
                timestamp_str = serialize_neo4j_datetime(rec['timestamp'])
                anomalies.append({
                    'id': generate_unique_id('curfew_late_exit', rec['entity_id'], 'HOSTEL_GATE', timestamp_str, str(rec['hour'])),
                    'type': 'curfew_violation',
                    'severity': 'critical',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'entity_role': rec['role'],
                    'location': 'HOSTEL_GATE',
                    'timestamp': timestamp_str,
                    'description': f"{rec['entity_name']} left hostel at {rec['hour']}:{rec['minute']:02d} (after 23:00 curfew - unauthorized exit)",
                    'details': {
                        'exit_hour': rec['hour'],
                        'exit_minute': rec['minute'],
                        'direction': 'OUT',
                        'curfew_time': '23:00',
                        'violation_type': 'Late exit from hostel'
                    },
                    'recommended_actions': [
                        "Immediate security alert",
                        "Contact warden/security personnel",
                        "Check for valid emergency reason",
                        "Review safety protocols"
                    ]
                })

        return anomalies

    def _detect_excessive_access(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect excessive access frequency (potential card sharing or anomalous behavior)"""
        anomalies = []

        with self.driver.session() as session:
            # Find entities with >10 zone accesses in a single hour
            result = session.run("""
                MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone)
                WHERE r.timestamp >= datetime($start_time)
                AND r.timestamp <= datetime($end_time)
                WITH e, z,
                     date(r.timestamp) as access_date,
                     r.timestamp.hour as hour,
                     count(r) as access_count
                WHERE access_count > 10
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       z.zone_id as zone_id,
                       z.name as zone_name,
                       access_date,
                       hour,
                       access_count
                ORDER BY access_count DESC
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                timestamp_obj = datetime.combine(rec['access_date'], datetime.min.time().replace(hour=rec['hour']))
                timestamp_str = serialize_neo4j_datetime(timestamp_obj)
                anomalies.append({
                    'id': generate_unique_id('excessive_access', rec['entity_id'], rec['zone_id'], timestamp_str, str(rec['access_count'])),
                    'type': 'excessive_access',
                    'severity': 'medium',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'entity_role': rec['role'],
                    'location': rec['zone_id'],
                    'timestamp': timestamp_str,
                    'description': f"{rec['entity_name']} accessed {rec['zone_name']} {rec['access_count']} times in hour {rec['hour']}:00 (unusual frequency)",
                    'details': {
                        'access_count': rec['access_count'],
                        'date': serialize_neo4j_datetime(rec['access_date']),
                        'hour': rec['hour'],
                        'threshold': 10
                    },
                    'recommended_actions': [
                        "Check for card sharing",
                        "Investigate bot/automated access",
                        "Review access pattern for legitimacy"
                    ]
                })

        return anomalies

    def _detect_booking_anomalies(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect booking no-shows (booked but never accessed during booking window)"""
        anomalies = []

        with self.driver.session() as session:
            # Find bookings where the entity never accessed the room during booking time
            result = session.run("""
                MATCH (e:Entity)-[b:BOOKED_ROOM]->(z:Zone)
                WHERE b.start_time >= datetime($start_time)
                AND b.start_time <= datetime($end_time)
                WITH e, b, z
                OPTIONAL MATCH (e)-[access:SWIPED_CARD]->(z)
                WHERE access.timestamp >= b.start_time
                AND access.timestamp <= b.end_time
                WITH e, b, z, count(access) as access_count
                WHERE access_count = 0
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       z.zone_id as room_id,
                       b.booking_id as booking_id,
                       b.start_time as start_time,
                       b.end_time as end_time
                ORDER BY b.start_time DESC
                LIMIT 100
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                timestamp_str = serialize_neo4j_datetime(rec['start_time'])
                anomalies.append({
                    'id': generate_unique_id('booking_no_show', rec['entity_id'], rec['room_id'], timestamp_str, str(rec['booking_id'])),
                    'type': 'booking_no_show',
                    'severity': 'low',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'location': rec['room_id'],
                    'timestamp': timestamp_str,
                    'description': f"{rec['entity_name']} booked {rec['room_id']} but never accessed it during booking window (resource waste)",
                    'details': {
                        'booking_id': rec['booking_id'],
                        'start_time': serialize_neo4j_datetime(rec['start_time']),
                        'end_time': serialize_neo4j_datetime(rec['end_time']),
                        'booking_duration_hours': (rec['end_time'] - rec['start_time']).seconds / 3600 if hasattr((rec['end_time'] - rec['start_time']), 'seconds') else 0
                    },
                    'recommended_actions': [
                        "Track no-show patterns",
                        "Implement booking penalties for repeat offenders",
                        "Send reminder notifications",
                        "Release unused bookings automatically"
                    ]
                })

        return anomalies

    def _detect_entry_without_exit(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect entries without corresponding exits (potential tailgating/piggybacking)"""
        anomalies = []

        with self.driver.session() as session:
            # Find entities with IN swipes but no matching OUT swipe within the same day
            result = session.run("""
                MATCH (e:Entity)-[entry:SWIPED_CARD {direction: 'IN'}]->(z:Zone)
                WHERE entry.timestamp >= datetime($start_time)
                AND entry.timestamp <= datetime($end_time)
                WITH e, z, entry, date(entry.timestamp) as entry_date
                OPTIONAL MATCH (e)-[exit:SWIPED_CARD {direction: 'OUT'}]->(z)
                WHERE date(exit.timestamp) = entry_date
                AND exit.timestamp > entry.timestamp
                WITH e, z, entry, entry_date, collect(exit) as exits
                WHERE size(exits) = 0
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       z.zone_id as zone_id,
                       z.name as zone_name,
                       entry.timestamp as entry_time,
                       entry_date as date
                ORDER BY entry.timestamp DESC
                LIMIT 100
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                timestamp_str = serialize_neo4j_datetime(rec['entry_time'])
                anomalies.append({
                    'id': generate_unique_id('entry_no_exit', rec['entity_id'], rec['zone_id'], timestamp_str),
                    'type': 'entry_without_exit',
                    'severity': 'medium',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'entity_role': rec['role'],
                    'location': rec['zone_id'],
                    'location_name': rec['zone_name'],
                    'timestamp': timestamp_str,
                    'description': f"{rec['entity_name']} entered {rec['zone_name']} but no exit recorded (potential tailgating or card lending)",
                    'details': {
                        'entry_time': timestamp_str,
                        'zone': rec['zone_id'],
                        'date': serialize_neo4j_datetime(rec['date']),
                        'anomaly_reason': 'No corresponding OUT swipe found after IN swipe'
                    },
                    'recommended_actions': [
                        "Check CCTV footage for tailgating",
                        "Verify if person left through alternate exit",
                        "Investigate possible card lending",
                        "Review badge-in/badge-out policy compliance"
                    ]
                })

        return anomalies

    def _detect_exit_without_entry(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect exits without corresponding entries (suspicious exit, possible piggybacking on entry)"""
        anomalies = []

        with self.driver.session() as session:
            # Find entities with OUT swipes but no matching IN swipe before it on the same day
            result = session.run("""
                MATCH (e:Entity)-[exit:SWIPED_CARD {direction: 'OUT'}]->(z:Zone)
                WHERE exit.timestamp >= datetime($start_time)
                AND exit.timestamp <= datetime($end_time)
                WITH e, z, exit, date(exit.timestamp) as exit_date
                OPTIONAL MATCH (e)-[entry:SWIPED_CARD {direction: 'IN'}]->(z)
                WHERE date(entry.timestamp) = exit_date
                AND entry.timestamp < exit.timestamp
                WITH e, z, exit, exit_date, collect(entry) as entries
                WHERE size(entries) = 0
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       z.zone_id as zone_id,
                       z.name as zone_name,
                       exit.timestamp as exit_time,
                       exit_date as date
                ORDER BY exit.timestamp DESC
                LIMIT 100
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                timestamp_str = serialize_neo4j_datetime(rec['exit_time'])
                anomalies.append({
                    'id': generate_unique_id('exit_no_entry', rec['entity_id'], rec['zone_id'], timestamp_str),
                    'type': 'exit_without_entry',
                    'severity': 'high',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'entity_role': rec['role'],
                    'location': rec['zone_id'],
                    'location_name': rec['zone_name'],
                    'timestamp': timestamp_str,
                    'description': f"{rec['entity_name']} exited {rec['zone_name']} without prior entry record (piggybacking suspected)",
                    'details': {
                        'exit_time': timestamp_str,
                        'zone': rec['zone_id'],
                        'date': serialize_neo4j_datetime(rec['date']),
                        'anomaly_reason': 'OUT swipe recorded without prior IN swipe'
                    },
                    'recommended_actions': [
                        "Review CCTV for unauthorized entry",
                        "Check for piggybacking on another person's entry",
                        "Investigate possible security breach",
                        "Verify card system integrity"
                    ]
                })

        return anomalies

    def _detect_abnormal_dwell_time(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect abnormally long stays in zones (potential security concern)"""
        anomalies = []

        # Maximum expected dwell times per zone type (in hours)
        max_dwell_times = {
            'LAB_101': 8, 'LAB_102': 8, 'LAB_305': 6,
            'LIB_ENT': 10, 'CAF_01': 3, 'GYM': 4,
            'ADMIN_LOBBY': 2, 'AUDITORIUM': 5,
            'HOSTEL_GATE': 1, 'SEM_01': 4,
            'ROOM_A1': 3, 'ROOM_A2': 3
        }

        with self.driver.session() as session:
            # Find entry-exit pairs with long dwell times
            result = session.run("""
                MATCH (e:Entity)-[entry:SWIPED_CARD {direction: 'IN'}]->(z:Zone)
                WHERE entry.timestamp >= datetime($start_time)
                AND entry.timestamp <= datetime($end_time)
                MATCH (e)-[exit:SWIPED_CARD {direction: 'OUT'}]->(z)
                WHERE exit.timestamp > entry.timestamp
                AND date(exit.timestamp) = date(entry.timestamp)
                WITH e, z, entry, exit,
                     duration.between(entry.timestamp, exit.timestamp).hours as dwell_hours,
                     duration.between(entry.timestamp, exit.timestamp).minutes as dwell_minutes
                WHERE dwell_hours >= 1
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       z.zone_id as zone_id,
                       z.name as zone_name,
                       entry.timestamp as entry_time,
                       exit.timestamp as exit_time,
                       dwell_hours,
                       dwell_minutes
                ORDER BY dwell_hours DESC
                LIMIT 50
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                zone_id = rec['zone_id']
                max_hours = max_dwell_times.get(zone_id, 8)
                dwell_hours = rec['dwell_hours']

                if dwell_hours > max_hours:
                    timestamp_str = serialize_neo4j_datetime(rec['entry_time'])
                    severity = 'critical' if dwell_hours > max_hours * 2 else 'high' if dwell_hours > max_hours * 1.5 else 'medium'

                    anomalies.append({
                        'id': generate_unique_id('abnormal_dwell', rec['entity_id'], rec['zone_id'], timestamp_str, str(dwell_hours)),
                        'type': 'abnormal_dwell_time',
                        'severity': severity,
                        'entity_id': rec['entity_id'],
                        'entity_name': rec['entity_name'],
                        'entity_role': rec['role'],
                        'location': rec['zone_id'],
                        'location_name': rec['zone_name'],
                        'timestamp': timestamp_str,
                        'description': f"{rec['entity_name']} stayed in {rec['zone_name']} for {dwell_hours}h {rec['dwell_minutes']}m (expected max: {max_hours}h)",
                        'details': {
                            'entry_time': timestamp_str,
                            'exit_time': serialize_neo4j_datetime(rec['exit_time']),
                            'dwell_hours': dwell_hours,
                            'dwell_minutes': rec['dwell_minutes'],
                            'expected_max_hours': max_hours,
                            'excess_hours': dwell_hours - max_hours
                        },
                        'recommended_actions': [
                            "Verify legitimate extended access need",
                            "Check for overnight stays in restricted areas",
                            "Review access authorization for extended periods",
                            "Investigate potential security or safety concerns"
                        ]
                    })

        return anomalies

    def _detect_consecutive_same_direction(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Detect consecutive swipes in the same direction (IN-IN or OUT-OUT) suggesting card sharing"""
        anomalies = []

        with self.driver.session() as session:
            # Find consecutive IN swipes without OUT in between
            result = session.run("""
                MATCH (e:Entity)-[r1:SWIPED_CARD]->(z:Zone)
                MATCH (e)-[r2:SWIPED_CARD]->(z)
                WHERE r1.timestamp >= datetime($start_time)
                AND r1.timestamp <= datetime($end_time)
                AND r2.timestamp > r1.timestamp
                AND r1.direction = r2.direction
                AND duration.between(r1.timestamp, r2.timestamp).hours < 2
                WITH e, z, r1, r2,
                     duration.between(r1.timestamp, r2.timestamp).minutes as minutes_between,
                     r1.direction as direction
                WHERE NOT EXISTS {
                    MATCH (e)-[middle:SWIPED_CARD]->(z)
                    WHERE middle.timestamp > r1.timestamp
                    AND middle.timestamp < r2.timestamp
                    AND middle.direction <> r1.direction
                }
                RETURN e.entity_id as entity_id,
                       e.name as entity_name,
                       e.role as role,
                       z.zone_id as zone_id,
                       z.name as zone_name,
                       r1.timestamp as first_swipe,
                       r2.timestamp as second_swipe,
                       direction,
                       minutes_between
                ORDER BY r1.timestamp DESC
                LIMIT 50
            """, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })

            for rec in result:
                timestamp_str = serialize_neo4j_datetime(rec['first_swipe'])
                direction = rec['direction']

                anomalies.append({
                    'id': generate_unique_id('consecutive_direction', rec['entity_id'], rec['zone_id'], timestamp_str, direction),
                    'type': 'consecutive_same_direction',
                    'severity': 'high' if direction == 'IN' else 'medium',
                    'entity_id': rec['entity_id'],
                    'entity_name': rec['entity_name'],
                    'entity_role': rec['role'],
                    'location': rec['zone_id'],
                    'location_name': rec['zone_name'],
                    'timestamp': timestamp_str,
                    'description': f"{rec['entity_name']} swiped {direction} twice at {rec['zone_name']} ({rec['minutes_between']} min apart) - possible card sharing",
                    'details': {
                        'first_swipe': timestamp_str,
                        'second_swipe': serialize_neo4j_datetime(rec['second_swipe']),
                        'direction': direction,
                        'minutes_between': rec['minutes_between'],
                        'anomaly_reason': f'Two consecutive {direction} swipes without opposite direction in between'
                    },
                    'recommended_actions': [
                        "Investigate possible card sharing/lending",
                        "Check for buddy punching",
                        "Review CCTV footage for verification",
                        "Verify card system is not malfunctioning"
                    ]
                })

        return anomalies

    def close(self):
        """Close database connection"""
        self.driver.close()
