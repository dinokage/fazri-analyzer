# backend/app/scripts/simple_zone_migration.py
import os
from neo4j import GraphDatabase
from datetime import datetime, timedelta
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleZoneMigration:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()

    def execute_migration(self):
        """Execute simplified zone migration"""
        print("🚀 Starting Simple Zone Migration...")
        print("=" * 50)
        
        try:
            # Step 1: Add zones
            self._add_zones()
            
            # Step 2: Create zone relationships
            self._create_zone_relationships()
            
            # Step 3: Add synthetic training data
            self._add_synthetic_data()
            
            # Step 4: Add latest/today's data
            self._add_latest_data()
            
            # Step 5: Verify
            self._verify_migration()
            
            print("\n🎉 Simple migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            print(f"\n❌ Migration failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _add_zones(self):
        """Add zone nodes - aligned with real data ingestion AP mappings"""
        print("🏢 Adding zones...")
        
        # Zones matching the AP to Zone mappings from ingest_real_data.py
        zones = [
            # ADMIN_LOBBY - AP_ADMIN_1 to AP_ADMIN_5
            {"zone_id": "ADMIN_LOBBY", "name": "Administrative Block Lobby", "zone_type": "LOBBY", "capacity": 50, "building": "Administrative Block", "floor": 1, "latitude": 26.1445, "longitude": 91.7362, "department": "Administration"},
            
            # AUDITORIUM - AP_AUD_1 to AP_AUD_5
            {"zone_id": "AUDITORIUM", "name": "Main Auditorium", "zone_type": "AUDITORIUM", "capacity": 500, "building": "Academic Block B", "floor": 1, "latitude": 26.1448, "longitude": 91.7365, "department": "Events"},
            
            # CAF_01 - AP_CAF_1 to AP_CAF_5
            {"zone_id": "CAF_01", "name": "Central Cafeteria", "zone_type": "CAFETERIA", "capacity": 200, "building": "Student Center", "floor": 1, "latitude": 26.1440, "longitude": 91.7360, "department": "Food Services"},
            
            # GYM - AP_GYM_1, AP_GYM_2
            {"zone_id": "GYM", "name": "Fitness Center", "zone_type": "GYM", "capacity": 80, "building": "Sports Complex", "floor": 1, "latitude": 26.1435, "longitude": 91.7355, "department": "Sports"},
            
            # HOSTEL_GATE - AP_HOSTEL_1 to AP_HOSTEL_5
            {"zone_id": "HOSTEL_GATE", "name": "Hostel Main Gate", "zone_type": "ENTRANCE", "capacity": 30, "building": "Hostel Block A", "floor": 0, "latitude": 26.1450, "longitude": 91.7370, "department": "Security"},
            
            # LAB_101 - AP_LAB_1, AP_LAB_2
            {"zone_id": "LAB_101", "name": "Computer Science Lab 101", "zone_type": "LAB", "capacity": 40, "building": "Academic Block A", "floor": 1, "latitude": 26.1442, "longitude": 91.7358, "department": "Computer Science"},
            
            # LAB_102 - AP_LAB_3, AP_ENG_1, AP_ENG_2, AP_ENG_5
            {"zone_id": "LAB_102", "name": "Engineering Lab 102", "zone_type": "LAB", "capacity": 40, "building": "Engineering Block", "floor": 1, "latitude": 26.1443, "longitude": 91.7359, "department": "Engineering"},
            
            # LAB_305 - AP_LAB_4, AP_LAB_5, AP_ENG_3, AP_ENG_4
            {"zone_id": "LAB_305", "name": "Advanced Lab 305", "zone_type": "LAB", "capacity": 35, "building": "Engineering Block", "floor": 3, "latitude": 26.1447, "longitude": 91.7368, "department": "Electronics Engineering"},
            
            # LIB_ENT - AP_LIB_1 to AP_LIB_5
            {"zone_id": "LIB_ENT", "name": "Library Main Entrance", "zone_type": "ENTRANCE", "capacity": 25, "building": "Library Building", "floor": 1, "latitude": 26.1443, "longitude": 91.7363, "department": "Library Services"},
            
            # SEM_01 - AP_SEM_1
            {"zone_id": "SEM_01", "name": "Seminar Hall 01", "zone_type": "SEMINAR", "capacity": 100, "building": "Academic Block C", "floor": 2, "latitude": 26.1446, "longitude": 91.7366, "department": "Academics"}
        ]
        
        with self.driver.session() as session:
            for zone in zones:
                session.run("""
                    MERGE (z:Zone {zone_id: $zone_id})
                    SET z.name = $name,
                        z.zone_type = $zone_type,
                        z.capacity = $capacity,
                        z.building = $building,
                        z.floor = $floor,
                        z.latitude = $latitude,
                        z.longitude = $longitude,
                        z.department = $department,
                        z.is_placeholder = false,
                        z.created_at = datetime()
                """, zone)
        
        print(f"   ✅ Added {len(zones)} zones")

    def _create_zone_relationships(self):
        """Create zone connections based on building proximity"""
        print("🔗 Creating zone connections...")
        
        connections = [
            # Admin building connections
            {"from": "ADMIN_LOBBY", "to": "LIB_ENT", "distance": 150, "time": 2},
            {"from": "ADMIN_LOBBY", "to": "CAF_01", "distance": 200, "time": 3},
            
            # Academic block connections
            {"from": "LAB_101", "to": "LAB_102", "distance": 50, "time": 1},
            {"from": "LAB_102", "to": "LAB_305", "distance": 100, "time": 2},
            {"from": "LAB_101", "to": "SEM_01", "distance": 120, "time": 2},
            
            # Cafeteria connections
            {"from": "CAF_01", "to": "LAB_101", "distance": 200, "time": 3},
            {"from": "CAF_01", "to": "LIB_ENT", "distance": 180, "time": 2},
            {"from": "CAF_01", "to": "AUDITORIUM", "distance": 150, "time": 2},
            
            # Sports/Hostel area
            {"from": "GYM", "to": "HOSTEL_GATE", "distance": 250, "time": 3},
            {"from": "HOSTEL_GATE", "to": "CAF_01", "distance": 300, "time": 4},
            
            # Auditorium connections
            {"from": "AUDITORIUM", "to": "SEM_01", "distance": 100, "time": 2},
            {"from": "AUDITORIUM", "to": "ADMIN_LOBBY", "distance": 180, "time": 2},
            
            # Library connections
            {"from": "LIB_ENT", "to": "SEM_01", "distance": 150, "time": 2},
            {"from": "LIB_ENT", "to": "LAB_101", "distance": 200, "time": 3}
        ]
        
        with self.driver.session() as session:
            for conn in connections:
                session.run("""
                    MATCH (z1:Zone {zone_id: $from})
                    MATCH (z2:Zone {zone_id: $to})
                    MERGE (z1)-[r:CONNECTED_TO]->(z2)
                    SET r.distance_meters = $distance,
                        r.walking_time_minutes = $time,
                        r.created_at = datetime()
                """, conn)
        
        print(f"   ✅ Created {len(connections)} connections")

    def _add_synthetic_data(self):
        """Add synthetic occupancy data for historical training - aligned with real data patterns"""
        print("📊 Adding synthetic historical data...")
        
        # Patterns based on realistic campus activity (matching card swipe/WiFi patterns)
        patterns = {
            "ADMIN_LOBBY": {
                "weekday": {8: 20, 9: 35, 10: 40, 11: 38, 12: 25, 13: 30, 14: 35, 15: 45, 16: 40, 17: 30, 18: 15},
                "weekend": {10: 8, 11: 6, 14: 5, 15: 4}
            },
            "AUDITORIUM": {
                "weekday": {9: 50, 10: 150, 11: 280, 12: 100, 14: 200, 15: 180, 16: 120, 19: 180, 20: 150},
                "weekend": {10: 30, 14: 100, 19: 200, 20: 180}
            },
            "CAF_01": {
                "weekday": {7: 30, 8: 80, 9: 60, 11: 100, 12: 150, 13: 180, 14: 120, 17: 80, 18: 120, 19: 140, 20: 100},
                "weekend": {9: 40, 12: 120, 13: 100, 18: 90, 19: 100}
            },
            "GYM": {
                "weekday": {6: 20, 7: 45, 8: 35, 17: 50, 18: 70, 19: 65, 20: 55, 21: 40},
                "weekend": {8: 25, 9: 40, 10: 45, 17: 45, 18: 50, 19: 45}
            },
            "HOSTEL_GATE": {
                "weekday": {6: 5, 7: 15, 8: 20, 9: 10, 17: 12, 18: 22, 19: 20, 20: 15, 21: 18, 22: 12},
                "weekend": {8: 5, 9: 12, 18: 15, 19: 18, 20: 14}
            },
            "LAB_101": {
                "weekday": {8: 10, 9: 35, 10: 38, 11: 36, 12: 15, 14: 32, 15: 35, 16: 30, 17: 20, 18: 15},
                "weekend": {10: 8, 14: 15, 15: 12}
            },
            "LAB_102": {
                "weekday": {8: 8, 9: 30, 10: 35, 11: 33, 12: 12, 14: 28, 15: 32, 16: 28, 17: 18},
                "weekend": {10: 6, 14: 12, 15: 10}
            },
            "LAB_305": {
                "weekday": {9: 15, 10: 25, 11: 28, 12: 10, 14: 20, 15: 26, 16: 22, 17: 15},
                "weekend": {11: 5, 14: 10, 15: 8}
            },
            "LIB_ENT": {
                "weekday": {8: 5, 9: 15, 10: 18, 11: 20, 12: 12, 14: 16, 15: 18, 16: 20, 17: 22, 18: 18, 19: 14, 20: 10, 21: 8},
                "weekend": {10: 5, 14: 12, 15: 14, 16: 12, 18: 10}
            },
            "SEM_01": {
                "weekday": {9: 40, 10: 80, 11: 75, 14: 70, 15: 85, 16: 60, 17: 30},
                "weekend": {10: 20, 14: 40, 15: 35}
            }
        }
        
        total_records = 0
        
        with self.driver.session() as session:
            for zone_id, zone_patterns in patterns.items():
                zone_records = 0
                
                # Generate data for last 30 days (excluding today)
                for day in range(1, 31):
                    date = datetime.now() - timedelta(days=day)
                    is_weekend = date.weekday() >= 5
                    
                    pattern = zone_patterns["weekend"] if is_weekend else zone_patterns["weekday"]
                    
                    for hour, base_occupancy in pattern.items():
                        # Add randomness
                        actual_occupancy = max(0, base_occupancy + random.randint(-5, 5))
                        timestamp = date.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
                        
                        session.run("""
                            MATCH (z:Zone {zone_id: $zone_id})
                            CREATE (sa:SpatialActivity {
                                zone_id: $zone_id,
                                timestamp: datetime($timestamp),
                                occupancy: $occupancy,
                                hour: $hour,
                                day_of_week: $day_of_week,
                                is_weekend: $is_weekend,
                                activity_type: 'SYNTHETIC',
                                created_at: datetime()
                            })
                            CREATE (sa)-[:OCCURRED_IN]->(z)
                        """, {
                            'zone_id': zone_id,
                            'timestamp': timestamp.isoformat(),
                            'occupancy': actual_occupancy,
                            'hour': hour,
                            'day_of_week': date.weekday() + 1,
                            'is_weekend': is_weekend
                        })
                        
                        zone_records += 1
                        total_records += 1
                
                print(f"   📊 {zone_id}: {zone_records} historical records")
        
        print(f"   ✅ Total historical: {total_records} synthetic records")

    def _add_latest_data(self):
        """Add latest/today's data with hourly granularity up to current hour"""
        print("🕐 Adding latest (today's) data...")
        
        now = datetime.now()
        current_hour = now.hour
        is_weekend = now.weekday() >= 5
        
        # Realistic hourly patterns for today (all zones)
        hourly_patterns = {
            "ADMIN_LOBBY": {
                "weekday": {7: 5, 8: 20, 9: 35, 10: 40, 11: 38, 12: 25, 13: 30, 14: 35, 15: 45, 16: 40, 17: 30, 18: 15, 19: 8},
                "weekend": {9: 3, 10: 8, 11: 6, 14: 5, 15: 4}
            },
            "AUDITORIUM": {
                "weekday": {9: 50, 10: 150, 11: 280, 12: 100, 14: 200, 15: 180, 16: 120, 17: 80, 18: 100, 19: 180, 20: 150},
                "weekend": {10: 30, 14: 100, 18: 150, 19: 200, 20: 180}
            },
            "CAF_01": {
                "weekday": {7: 30, 8: 80, 9: 60, 10: 40, 11: 100, 12: 150, 13: 180, 14: 120, 15: 60, 16: 40, 17: 80, 18: 120, 19: 140, 20: 100},
                "weekend": {9: 40, 10: 60, 12: 120, 13: 100, 18: 90, 19: 100}
            },
            "GYM": {
                "weekday": {6: 20, 7: 45, 8: 35, 9: 20, 16: 30, 17: 50, 18: 70, 19: 65, 20: 55, 21: 40},
                "weekend": {8: 25, 9: 40, 10: 45, 17: 45, 18: 50, 19: 45}
            },
            "HOSTEL_GATE": {
                "weekday": {6: 5, 7: 15, 8: 20, 9: 10, 17: 12, 18: 22, 19: 20, 20: 15, 21: 18, 22: 12},
                "weekend": {8: 5, 9: 12, 18: 15, 19: 18, 20: 14}
            },
            "LAB_101": {
                "weekday": {8: 10, 9: 35, 10: 38, 11: 36, 12: 15, 13: 20, 14: 32, 15: 35, 16: 30, 17: 20, 18: 15, 19: 10},
                "weekend": {10: 8, 14: 15, 15: 12}
            },
            "LAB_102": {
                "weekday": {8: 8, 9: 30, 10: 35, 11: 33, 12: 12, 14: 28, 15: 32, 16: 28, 17: 18},
                "weekend": {10: 6, 14: 12, 15: 10}
            },
            "LAB_305": {
                "weekday": {9: 15, 10: 25, 11: 28, 12: 10, 14: 20, 15: 26, 16: 22, 17: 15},
                "weekend": {11: 5, 14: 10, 15: 8}
            },
            "LIB_ENT": {
                "weekday": {8: 5, 9: 15, 10: 18, 11: 20, 12: 12, 14: 16, 15: 18, 16: 20, 17: 22, 18: 18, 19: 14, 20: 10, 21: 8},
                "weekend": {10: 5, 14: 12, 15: 14, 16: 12, 18: 10}
            },
            "SEM_01": {
                "weekday": {9: 40, 10: 80, 11: 75, 12: 20, 14: 70, 15: 85, 16: 60, 17: 30},
                "weekend": {10: 20, 14: 40, 15: 35}
            }
        }
        
        total_records = 0
        
        with self.driver.session() as session:
            for zone_id, patterns in hourly_patterns.items():
                zone_records = 0
                pattern = patterns["weekend"] if is_weekend else patterns["weekday"]
                
                # Add data for each hour up to current hour
                for hour in range(current_hour + 1):
                    if hour in pattern:
                        base_occupancy = pattern[hour]
                    else:
                        # Default low occupancy for hours not in pattern
                        base_occupancy = random.randint(1, 5)
                    
                    # Add some randomness
                    actual_occupancy = max(0, base_occupancy + random.randint(-3, 3))
                    
                    # Create timestamp for today at this hour
                    timestamp = now.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
                    
                    session.run("""
                        MATCH (z:Zone {zone_id: $zone_id})
                        CREATE (sa:SpatialActivity {
                            zone_id: $zone_id,
                            timestamp: datetime($timestamp),
                            occupancy: $occupancy,
                            hour: $hour,
                            day_of_week: $day_of_week,
                            is_weekend: $is_weekend,
                            activity_type: 'LIVE',
                            created_at: datetime()
                        })
                        CREATE (sa)-[:OCCURRED_IN]->(z)
                    """, {
                        'zone_id': zone_id,
                        'timestamp': timestamp.isoformat(),
                        'occupancy': actual_occupancy,
                        'hour': hour,
                        'day_of_week': now.weekday() + 1,
                        'is_weekend': is_weekend
                    })
                    
                    zone_records += 1
                    total_records += 1
                
                # Update zone's current occupancy
                current_occupancy = pattern.get(current_hour, random.randint(1, 5)) + random.randint(-3, 3)
                current_occupancy = max(0, current_occupancy)
                current_timestamp = now.replace(second=0, microsecond=0)
                
                session.run("""
                    MATCH (z:Zone {zone_id: $zone_id})
                    SET z.current_occupancy = $occupancy,
                        z.last_updated = datetime($timestamp)
                """, {
                    'zone_id': zone_id,
                    'occupancy': current_occupancy,
                    'timestamp': current_timestamp.isoformat()
                })
                
                print(f"   🕐 {zone_id}: {zone_records} today's records (current: {current_occupancy})")
        
        print(f"   ✅ Total today's records: {total_records}")

    def add_realtime_update(self):
        """Add a single real-time update for all zones (call this periodically)"""
        print("⚡ Adding real-time update...")
        
        now = datetime.now()
        current_hour = now.hour
        is_weekend = now.weekday() >= 5
        
        # Base patterns for current hour estimation
        base_patterns = {
            "ADMIN_LOBBY": 30 if not is_weekend and 8 <= current_hour <= 17 else 5,
            "AUDITORIUM": 150 if not is_weekend and 9 <= current_hour <= 16 else 50,
            "CAF_01": 120 if 11 <= current_hour <= 14 or 18 <= current_hour <= 20 else 50,
            "GYM": 50 if 6 <= current_hour <= 8 or 17 <= current_hour <= 21 else 15,
            "HOSTEL_GATE": 15 if 7 <= current_hour <= 9 or 17 <= current_hour <= 22 else 5,
            "LAB_101": 30 if 9 <= current_hour <= 17 and not is_weekend else 5,
            "LAB_102": 28 if 9 <= current_hour <= 17 and not is_weekend else 4,
            "LAB_305": 22 if 9 <= current_hour <= 17 and not is_weekend else 3,
            "LIB_ENT": 18 if 9 <= current_hour <= 21 else 3,
            "SEM_01": 60 if 9 <= current_hour <= 17 and not is_weekend else 10
        }
        
        with self.driver.session() as session:
            for zone_id, base_occupancy in base_patterns.items():
                occupancy = max(0, base_occupancy + random.randint(-8, 8))
                timestamp = now.replace(second=0, microsecond=0)
                
                # Update zone's current occupancy
                session.run("""
                    MATCH (z:Zone {zone_id: $zone_id})
                    SET z.current_occupancy = $occupancy,
                        z.last_updated = datetime($timestamp)
                """, {
                    'zone_id': zone_id,
                    'occupancy': occupancy,
                    'timestamp': timestamp.isoformat()
                })
                
                # Also create a spatial activity record
                session.run("""
                    MATCH (z:Zone {zone_id: $zone_id})
                    CREATE (sa:SpatialActivity {
                        zone_id: $zone_id,
                        timestamp: datetime($timestamp),
                        occupancy: $occupancy,
                        hour: $hour,
                        day_of_week: $day_of_week,
                        is_weekend: $is_weekend,
                        activity_type: 'REALTIME',
                        created_at: datetime()
                    })
                    CREATE (sa)-[:OCCURRED_IN]->(z)
                """, {
                    'zone_id': zone_id,
                    'timestamp': timestamp.isoformat(),
                    'occupancy': occupancy,
                    'hour': current_hour,
                    'day_of_week': now.weekday() + 1,
                    'is_weekend': is_weekend
                })
                
                print(f"   ⚡ {zone_id}: {occupancy}")
        
        print("   ✅ Real-time update complete")

    def _verify_migration(self):
        """Verify migration success"""
        print("🔍 Verifying migration...")
        
        with self.driver.session() as session:
            zones = session.run("MATCH (z:Zone) RETURN count(z) as count").single()["count"]
            connections = session.run("MATCH ()-[r:CONNECTED_TO]->() RETURN count(r) as count").single()["count"]
            activities = session.run("MATCH (sa:SpatialActivity) RETURN count(sa) as count").single()["count"]
            
            # Check today's data
            today_activities = session.run("""
                MATCH (sa:SpatialActivity)
                WHERE sa.timestamp >= datetime({year: $year, month: $month, day: $day})
                RETURN count(sa) as count
            """, {
                'year': datetime.now().year,
                'month': datetime.now().month,
                'day': datetime.now().day
            }).single()["count"]
            
            # Get zone list
            zone_list = session.run("""
                MATCH (z:Zone)
                RETURN z.zone_id as zone_id, z.name as name, z.current_occupancy as occupancy
                ORDER BY z.zone_id
            """)
            
            print(f"   📊 Results:")
            print(f"      - Zones: {zones}")
            print(f"      - Connections: {connections}")
            print(f"      - Total Activities: {activities}")
            print(f"      - Today's Activities: {today_activities}")
            print(f"   🏢 Zones created:")
            for record in zone_list:
                occ = record['occupancy'] if record['occupancy'] else 0
                print(f"      - {record['zone_id']}: {record['name']} (current: {occ})")
            
            if zones >= 10 and activities > 0 and today_activities > 0:
                print("   ✅ Migration verified successfully!")
                return True
            else:
                print("   ❌ Migration verification failed!")
                return False

    def clean_zones(self):
        """Remove all zone data"""
        print("🧹 Cleaning zone data...")
        
        with self.driver.session() as session:
            session.run("MATCH (sa:SpatialActivity) DETACH DELETE sa")
            session.run("MATCH ()-[r:CONNECTED_TO]->() DELETE r")
            session.run("MATCH (z:Zone) DETACH DELETE z")
            
        print("   ✅ Cleanup completed")

    def refresh_today_data(self):
        """Clear and regenerate today's data only"""
        print("🔄 Refreshing today's data...")
        
        now = datetime.now()
        
        with self.driver.session() as session:
            # Delete today's activities
            result = session.run("""
                MATCH (sa:SpatialActivity)
                WHERE sa.timestamp >= datetime({year: $year, month: $month, day: $day})
                DETACH DELETE sa
                RETURN count(sa) as count
            """, {
                'year': now.year,
                'month': now.month,
                'day': now.day
            })
            deleted = result.single()["count"]
            
            print(f"   🗑️ Deleted {deleted} old records")
        
        # Add fresh today's data
        self._add_latest_data()
        print("   ✅ Today's data refreshed")

    def sync_with_real_data(self):
        """Sync zones with real data ingestion - ensures zones exist before ingestion"""
        print("🔄 Syncing zones for real data ingestion...")
        
        with self.driver.session() as session:
            # Check if zones exist
            zone_count = session.run("MATCH (z:Zone) RETURN count(z) as count").single()["count"]
            
            if zone_count < 10:
                print("   ⚠️ Not all zones exist, adding missing zones...")
                self._add_zones()
            else:
                print(f"   ✅ All {zone_count} zones exist")
            
            # Ensure connections exist
            conn_count = session.run("MATCH ()-[r:CONNECTED_TO]->() RETURN count(r) as count").single()["count"]
            
            if conn_count < 10:
                print("   ⚠️ Missing connections, creating...")
                self._create_zone_relationships()
            else:
                print(f"   ✅ {conn_count} connections exist")
        
        print("   ✅ Sync complete - ready for real data ingestion")


def main():
    """Main function"""
    import sys
    
    print("Simple Zone Migration (Aligned with Real Data)")
    print("=" * 50)
    
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
    
    # Check for command line arguments
    action = sys.argv[1] if len(sys.argv) > 1 else "migrate"
    
    try:
        with SimpleZoneMigration(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD) as migration:
            
            if action == "migrate":
                success = migration.execute_migration()
            elif action == "clean":
                migration.clean_zones()
                success = True
            elif action == "refresh":
                migration.refresh_today_data()
                success = True
            elif action == "realtime":
                migration.add_realtime_update()
                success = True
            elif action == "sync":
                migration.sync_with_real_data()
                success = True
            else:
                print(f"Unknown action: {action}")
                print("Usage: python simple_zone_migration.py [migrate|clean|refresh|realtime|sync]")
                success = False
            
            if success:
                print("\n🎉 Success! Your zones are ready.")
                print("\nZones created (matching real data ingestion):")
                print("  • ADMIN_LOBBY  - AP_ADMIN_1 to AP_ADMIN_5")
                print("  • AUDITORIUM   - AP_AUD_1 to AP_AUD_5")
                print("  • CAF_01       - AP_CAF_1 to AP_CAF_5")
                print("  • GYM          - AP_GYM_1, AP_GYM_2")
                print("  • HOSTEL_GATE  - AP_HOSTEL_1 to AP_HOSTEL_5")
                print("  • LAB_101      - AP_LAB_1, AP_LAB_2")
                print("  • LAB_102      - AP_LAB_3, AP_ENG_1, AP_ENG_2, AP_ENG_5")
                print("  • LAB_305      - AP_LAB_4, AP_LAB_5, AP_ENG_3, AP_ENG_4")
                print("  • LIB_ENT      - AP_LIB_1 to AP_LIB_5")
                print("  • SEM_01       - AP_SEM_1")
                print("\nTest with these Postman endpoints:")
                print("• GET http://localhost:8000/api/v1/spatial/zones")
                print("• GET http://localhost:8000/api/v1/spatial/zones/LAB_101")
                print("• GET http://localhost:8000/api/v1/spatial/campus/summary")
                print("\nCommands:")
                print("• python simple_zone_migration.py migrate  - Full migration")
                print("• python simple_zone_migration.py clean    - Remove all data")
                print("• python simple_zone_migration.py refresh  - Refresh today's data")
                print("• python simple_zone_migration.py realtime - Add single real-time update")
                print("• python simple_zone_migration.py sync     - Sync zones for real data ingestion")
            else:
                print("\n❌ Operation failed.")
                
    except Exception as e:
        print(f"\n💥 Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
