# backend/app/scripts/simple_zone_migration.py
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
            
            # Step 4: Verify
            self._verify_migration()
            
            print("\n🎉 Simple migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            print(f"\n❌ Migration failed: {str(e)}")
            return False

    def _add_zones(self):
        """Add zone nodes"""
        print("🏢 Adding zones...")
        
        zones = [
            {"zone_id": "ADMIN_LOBBY", "name": "Administrative Block Lobby", "zone_type": "LOBBY", "capacity": 10, "building": "Administrative Block", "floor": 1, "latitude": 26.1445, "longitude": 91.7362, "department": "Administration"},
            {"zone_id": "AUDITORIUM", "name": "Main Auditorium", "zone_type": "AUDITORIUM", "capacity": 10, "building": "Academic Block B", "floor": 1, "latitude": 26.1448, "longitude": 91.7365, "department": "Events"},
            {"zone_id": "CAF_01", "name": "Central Cafeteria", "zone_type": "CAFETERIA", "capacity": 10, "building": "Student Center", "floor": 1, "latitude": 26.1440, "longitude": 91.7360, "department": "Food Services"},
            {"zone_id": "GYM", "name": "Fitness Center", "zone_type": "GYM", "capacity": 10, "building": "Sports Complex", "floor": 1, "latitude": 26.1435, "longitude": 91.7355, "department": "Sports"},
            {"zone_id": "HOSTEL_GATE", "name": "Hostel Main Gate", "zone_type": "ENTRANCE", "capacity": 10, "building": "Hostel Block A", "floor": 0, "latitude": 26.1450, "longitude": 91.7370, "department": "Security"},
            {"zone_id": "LAB_101", "name": "Computer Science Lab 101", "zone_type": "LAB", "capacity": 10, "building": "Academic Block A", "floor": 1, "latitude": 26.1442, "longitude": 91.7358, "department": "Computer Science"},
            {"zone_id": "LAB_306", "name": "Electronics Lab 306", "zone_type": "LAB", "capacity": 10, "building": "Engineering Block", "floor": 3, "latitude": 26.1447, "longitude": 91.7368, "department": "Electronics Engineering"},
            {"zone_id": "LIB_ENT", "name": "Library Main Entrance", "zone_type": "ENTRANCE", "capacity": 10, "building": "Library Building", "floor": 1, "latitude": 26.1443, "longitude": 91.7363, "department": "Library Services"}
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
                        z.created_at = datetime()
                """, zone)
        
        print(f"   ✅ Added {len(zones)} zones")

    def _create_zone_relationships(self):
        """Create zone connections"""
        print("🔗 Creating zone connections...")
        
        connections = [
            {"from": "ADMIN_LOBBY", "to": "LIB_ENT", "distance": 150, "time": 2},
            {"from": "CAF_01", "to": "LAB_101", "distance": 200, "time": 3},
            {"from": "LAB_101", "to": "LAB_306", "distance": 300, "time": 4},
            {"from": "GYM", "to": "HOSTEL_GATE", "distance": 250, "time": 3}
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
        """Add synthetic occupancy data"""
        print("📊 Adding synthetic data...")
        
        patterns = {
            "ADMIN_LOBBY": {"weekday": {9: 35, 10: 40, 14: 35, 15: 45, 16: 40}, "weekend": {10: 8, 14: 5}},
            "AUDITORIUM": {"weekday": {10: 150, 11: 280, 14: 200, 19: 180}, "weekend": {14: 100, 19: 200}},
            "CAF_01": {"weekday": {8: 80, 12: 150, 13: 180, 19: 140}, "weekend": {12: 120, 19: 100}},
            "GYM": {"weekday": {7: 45, 18: 70, 19: 65, 20: 55}, "weekend": {9: 40, 18: 50}},
            "HOSTEL_GATE": {"weekday": {8: 20, 18: 22, 19: 20}, "weekend": {9: 12, 19: 18}},
            "LAB_101": {"weekday": {9: 35, 10: 38, 14: 32, 15: 35}, "weekend": {14: 15}},
            "LAB_306": {"weekday": {10: 25, 11: 28, 15: 26}, "weekend": {14: 10}},
            "LIB_ENT": {"weekday": {9: 15, 14: 16, 16: 20, 19: 14}, "weekend": {14: 12, 18: 10}}
        }
        
        total_records = 0
        
        with self.driver.session() as session:
            for zone_id, zone_patterns in patterns.items():
                zone_records = 0
                
                # Generate data for last 30 days
                for day in range(30):
                    date = datetime.now() - timedelta(days=day)
                    is_weekend = date.weekday() >= 5
                    
                    pattern = zone_patterns["weekend"] if is_weekend else zone_patterns["weekday"]
                    
                    for hour, base_occupancy in pattern.items():
                        # Add randomness
                        actual_occupancy = max(0, base_occupancy + random.randint(-3, 3))
                        timestamp = date.replace(hour=hour, minute=random.randint(0, 59))
                        
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
                
                print(f"   📊 {zone_id}: {zone_records} records")
        
        print(f"   ✅ Total: {total_records} synthetic records")

    def _verify_migration(self):
        """Verify migration success"""
        print("🔍 Verifying migration...")
        
        with self.driver.session() as session:
            zones = session.run("MATCH (z:Zone) RETURN count(z) as count").single()["count"]
            connections = session.run("MATCH ()-[r:CONNECTED_TO]->() RETURN count(r) as count").single()["count"]
            activities = session.run("MATCH (sa:SpatialActivity) RETURN count(sa) as count").single()["count"]
            
            print(f"   📊 Results:")
            print(f"      - Zones: {zones}")
            print(f"      - Connections: {connections}")
            print(f"      - Activities: {activities}")
            
            if zones >= 8 and activities > 0:
                print("   ✅ Migration verified successfully!")
                return True
            else:
                print("   ❌ Migration verification failed!")
                return False

    def clean_zones(self):
        """Remove all zone data"""
        print("🧹 Cleaning zone data...")
        
        with self.driver.session() as session:
            session.run("MATCH (sa:SpatialActivity) DELETE sa")
            session.run("MATCH ()-[r:CONNECTED_TO]->() DELETE r")
            session.run("MATCH (z:Zone) DELETE z")
            
        print("   ✅ Cleanup completed")

def main():
    """Main function"""
    print("Simple Zone Migration")
    print("=" * 30)
    
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "Pressword@69"
    
    try:
        with SimpleZoneMigration(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD) as migration:
            success = migration.execute_migration()
            
            if success:
                print("\n🎉 Success! Your zones are ready.")
                print("\nTest with these Postman endpoints:")
                print("• GET http://localhost:8000/api/v1/spatial/zones")
                print("• GET http://localhost:8000/api/v1/spatial/zones/LAB_101")
                print("• GET http://localhost:8000/api/v1/spatial/campus/summary")
            else:
                print("\n❌ Migration failed.")
                
    except Exception as e:
        print(f"\n💥 Error: {str(e)}")

if __name__ == "__main__":
    main()