#!/usr/bin/env python3
"""
Ingest real CSV data into Neo4j graph database
This script creates Entity nodes and links them to Zone activities
"""

from neo4j import GraphDatabase
import csv
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealDataIngestion:
    def __init__(self, uri: str, user: str, password: str, data_dir: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.data_dir = Path(data_dir)

        # Zone to WiFi AP mapping
        self.ap_to_zone = {
            'AP_ADMIN_1': 'ADMIN_LOBBY', 'AP_ADMIN_2': 'ADMIN_LOBBY', 'AP_ADMIN_3': 'ADMIN_LOBBY',
            'AP_ADMIN_4': 'ADMIN_LOBBY', 'AP_ADMIN_5': 'ADMIN_LOBBY',
            'AP_AUD_1': 'AUDITORIUM', 'AP_AUD_2': 'AUDITORIUM', 'AP_AUD_3': 'AUDITORIUM',
            'AP_AUD_4': 'AUDITORIUM', 'AP_AUD_5': 'AUDITORIUM',
            'AP_CAF_1': 'CAF_01', 'AP_CAF_2': 'CAF_01', 'AP_CAF_3': 'CAF_01',
            'AP_CAF_4': 'CAF_01', 'AP_CAF_5': 'CAF_01',
            'AP_LAB_1': 'LAB_101', 'AP_LAB_2': 'LAB_101',
            'AP_LAB_3': 'LAB_102', 'AP_LAB_4': 'LAB_305', 'AP_LAB_5': 'LAB_305',
            'AP_LIB_1': 'LIB_ENT', 'AP_LIB_2': 'LIB_ENT', 'AP_LIB_3': 'LIB_ENT',
            'AP_LIB_4': 'LIB_ENT', 'AP_LIB_5': 'LIB_ENT',
            'AP_GYM_1': 'GYM', 'AP_GYM_2': 'GYM',
            'AP_HOSTEL_1': 'HOSTEL_GATE', 'AP_HOSTEL_2': 'HOSTEL_GATE',
            'AP_HOSTEL_3': 'HOSTEL_GATE', 'AP_HOSTEL_4': 'HOSTEL_GATE', 'AP_HOSTEL_5': 'HOSTEL_GATE',
            'AP_ENG_1': 'LAB_102', 'AP_ENG_2': 'LAB_102', 'AP_ENG_3': 'LAB_305',
            'AP_ENG_4': 'LAB_305', 'AP_ENG_5': 'LAB_102',
            'AP_SEM_1': 'SEM_01'
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()

    def execute_ingestion(self):
        """Main ingestion pipeline"""
        print("\n" + "=" * 80)
        print("REAL DATA INGESTION PIPELINE")
        print("=" * 80)

        try:
            # Step 1: Ingest Entities
            self._ingest_entities()

            # Step 2: Ingest Card Swipes
            self._ingest_card_swipes()

            # Step 3: Ingest WiFi Associations
            self._ingest_wifi_logs()

            # Step 4: Ingest CCTV Frames
            self._ingest_cctv_frames()

            # Step 5: Ingest Library Checkouts
            self._ingest_library_checkouts()

            # Step 6: Ingest Lab Bookings
            self._ingest_lab_bookings()

            # Step 7: Create hourly occupancy aggregations
            self._create_occupancy_aggregations()

            # Step 8: Verify
            self._verify_ingestion()

            print("\n" + "=" * 80)
            print("✅ DATA INGESTION COMPLETE")
            print("=" * 80)
            return True

        except Exception as e:
            logger.error(f"Ingestion failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _ingest_entities(self):
        """Ingest student/staff profiles as Entity nodes"""
        print("\n📋 Ingesting Entities...")

        csv_path = self.data_dir / "student_staff_profiles.csv"

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            entities = list(reader)

        logger.info(f"Found {len(entities)} entities to ingest")

        with self.driver.session() as session:
            # Batch insert for performance
            batch_size = 1000
            for i in range(0, len(entities), batch_size):
                batch = entities[i:i+batch_size]

                session.run("""
                    UNWIND $entities AS entity
                    MERGE (e:Entity {entity_id: entity.entity_id})
                    SET e.name = entity.name,
                        e.role = entity.role,
                        e.email = entity.email,
                        e.department = entity.department,
                        e.student_id = entity.student_id,
                        e.staff_id = entity.staff_id,
                        e.card_id = entity.card_id,
                        e.device_hash = entity.device_hash,
                        e.face_id = entity.face_id,
                        e.ingested_at = datetime()
                """, {'entities': batch})

                logger.info(f"  Ingested {min(i+batch_size, len(entities))}/{len(entities)} entities")

        print(f"  ✅ Ingested {len(entities)} entities")

    def _ingest_card_swipes(self):
        """Ingest card swipes and link to entities and zones"""
        print("\n💳 Ingesting Card Swipes...")

        csv_path = self.data_dir / "campus_card_swipes_augmented.csv"

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            swipes = list(reader)

        logger.info(f"Found {len(swipes)} card swipes to ingest")

        with self.driver.session() as session:
            batch_size = 1000
            for i in range(0, len(swipes), batch_size):
                batch = swipes[i:i+batch_size]

                session.run("""
                    UNWIND $swipes AS swipe
                    MATCH (e:Entity {card_id: swipe.card_id})
                    MATCH (z:Zone {zone_id: swipe.location_id})
                    CREATE (e)-[:SWIPED_CARD {
                        timestamp: datetime(swipe.timestamp),
                        location_id: swipe.location_id
                    }]->(z)
                """, {'swipes': batch})

                logger.info(f"  Ingested {min(i+batch_size, len(swipes))}/{len(swipes)} card swipes")

        print(f"  ✅ Ingested {len(swipes)} card swipes")

    def _ingest_wifi_logs(self):
        """Ingest WiFi associations and link to entities and zones"""
        print("\n📶 Ingesting WiFi Logs...")

        csv_path = self.data_dir / "wifi_associations_logs_augmented.csv"

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            logs = list(reader)

        logger.info(f"Found {len(logs)} WiFi logs to ingest")

        # Map AP to Zone and prepare data
        enhanced_logs = []
        for log in logs:
            zone_id = self.ap_to_zone.get(log['ap_id'])
            if zone_id:
                enhanced_logs.append({
                    'device_hash': log['device_hash'],
                    'ap_id': log['ap_id'],
                    'zone_id': zone_id,
                    'timestamp': log['timestamp']
                })

        logger.info(f"Mapped {len(enhanced_logs)} WiFi logs to zones")

        with self.driver.session() as session:
            batch_size = 1000
            for i in range(0, len(enhanced_logs), batch_size):
                batch = enhanced_logs[i:i+batch_size]

                session.run("""
                    UNWIND $logs AS log
                    MATCH (e:Entity {device_hash: log.device_hash})
                    MATCH (z:Zone {zone_id: log.zone_id})
                    CREATE (e)-[:CONNECTED_TO_WIFI {
                        timestamp: datetime(log.timestamp),
                        ap_id: log.ap_id,
                        zone_id: log.zone_id
                    }]->(z)
                """, {'logs': batch})

                logger.info(f"  Ingested {min(i+batch_size, len(enhanced_logs))}/{len(enhanced_logs)} WiFi logs")

        print(f"  ✅ Ingested {len(enhanced_logs)} WiFi associations")

    def _ingest_cctv_frames(self):
        """Ingest CCTV detections and link to entities and zones"""
        print("\n📹 Ingesting CCTV Frames...")

        csv_path = self.data_dir / "cctv_frames_augmented.csv"

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            frames = list(reader)

        logger.info(f"Found {len(frames)} CCTV frames to ingest")

        # Only process frames with face_id
        frames_with_faces = [f for f in frames if f['face_id']]
        logger.info(f"  {len(frames_with_faces)} frames have face detections")

        with self.driver.session() as session:
            batch_size = 1000
            for i in range(0, len(frames_with_faces), batch_size):
                batch = frames_with_faces[i:i+batch_size]

                session.run("""
                    UNWIND $frames AS frame
                    MATCH (e:Entity {face_id: frame.face_id})
                    MATCH (z:Zone {zone_id: frame.location_id})
                    CREATE (e)-[:DETECTED_IN {
                        timestamp: datetime(frame.timestamp),
                        frame_id: frame.frame_id,
                        face_id: frame.face_id,
                        location_id: frame.location_id
                    }]->(z)
                """, {'frames': batch})

                logger.info(f"  Ingested {min(i+batch_size, len(frames_with_faces))}/{len(frames_with_faces)} CCTV detections")

        print(f"  ✅ Ingested {len(frames_with_faces)} CCTV detections")

    def _ingest_library_checkouts(self):
        """Ingest library checkouts"""
        print("\n📚 Ingesting Library Checkouts...")

        csv_path = self.data_dir / "library_checkouts_augmented.csv"

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            checkouts = list(reader)

        logger.info(f"Found {len(checkouts)} library checkouts")

        with self.driver.session() as session:
            batch_size = 1000
            for i in range(0, len(checkouts), batch_size):
                batch = checkouts[i:i+batch_size]

                session.run("""
                    UNWIND $checkouts AS checkout
                    MATCH (e:Entity {entity_id: checkout.entity_id})
                    CREATE (e)-[:CHECKED_OUT_BOOK {
                        timestamp: datetime(checkout.timestamp),
                        checkout_id: checkout.checkout_id,
                        book_id: checkout.book_id
                    }]->(:Book {book_id: checkout.book_id})
                """, {'checkouts': batch})

                logger.info(f"  Ingested {min(i+batch_size, len(checkouts))}/{len(checkouts)} checkouts")

        print(f"  ✅ Ingested {len(checkouts)} library checkouts")

    def _ingest_lab_bookings(self):
        """Ingest lab/room bookings"""
        print("\n🔬 Ingesting Lab Bookings...")

        csv_path = self.data_dir / "lab_bookings_augmented.csv"

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            bookings = list(reader)

        logger.info(f"Found {len(bookings)} lab bookings")

        with self.driver.session() as session:
            batch_size = 1000
            for i in range(0, len(bookings), batch_size):
                batch = bookings[i:i+batch_size]

                # Create bookings - link to zone if exists, otherwise create placeholder
                session.run("""
                    UNWIND $bookings AS booking
                    MATCH (e:Entity {entity_id: booking.entity_id})
                    MERGE (z:Zone {zone_id: booking.room_id})
                    ON CREATE SET z.name = booking.room_id,
                                  z.is_placeholder = true,
                                  z.capacity = 30
                    CREATE (e)-[:BOOKED_ROOM {
                        booking_id: booking.booking_id,
                        start_time: datetime(booking.start_time),
                        end_time: datetime(booking.end_time),
                        attended: booking.attended,
                        room_id: booking.room_id
                    }]->(z)
                """, {'bookings': batch})

                logger.info(f"  Ingested {min(i+batch_size, len(bookings))}/{len(bookings)} bookings")

        print(f"  ✅ Ingested {len(bookings)} lab bookings")

    def _create_occupancy_aggregations(self):
        """Create hourly occupancy counts per zone for anomaly detection"""
        print("\n📊 Creating Occupancy Aggregations...")

        with self.driver.session() as session:
            # Aggregate card swipes by zone and hour
            logger.info("  Aggregating card swipes...")
            session.run("""
                MATCH (e:Entity)-[s:SWIPED_CARD]->(z:Zone)
                WITH z,
                     date(s.timestamp) as activity_date,
                     s.timestamp.hour as hour,
                     s.timestamp.dayOfWeek as day_of_week,
                     count(DISTINCT e) as occupancy_count,
                     s.timestamp.year as year,
                     s.timestamp.month as month,
                     s.timestamp.day as day
                MERGE (sa:SpatialActivity {
                    zone_id: z.zone_id,
                    date: activity_date,
                    hour: hour
                })
                SET sa.occupancy = occupancy_count,
                    sa.day_of_week = day_of_week,
                    sa.is_weekend = (day_of_week >= 6),
                    sa.timestamp = datetime({year: year, month: month, day: day, hour: hour, minute: 0}),
                    sa.activity_type = 'CARD_SWIPE_AGGREGATED',
                    sa.created_at = datetime()
                MERGE (sa)-[:OCCURRED_IN]->(z)
            """)

            # Count aggregated activities
            result = session.run("""
                MATCH (sa:SpatialActivity {activity_type: 'CARD_SWIPE_AGGREGATED'})
                RETURN count(sa) as aggregated_count
            """)
            agg_count = result.single()['aggregated_count']

            print(f"  ✅ Created {agg_count} hourly occupancy aggregations")

    def _verify_ingestion(self):
        """Verify data was ingested correctly"""
        print("\n🔍 Verifying Ingestion...")

        with self.driver.session() as session:
            # Count entities
            entity_count = session.run("MATCH (e:Entity) RETURN count(e) as count").single()['count']
            print(f"  📋 Entities: {entity_count}")

            # Count card swipes
            swipe_count = session.run("MATCH ()-[r:SWIPED_CARD]->() RETURN count(r) as count").single()['count']
            print(f"  💳 Card Swipes: {swipe_count}")

            # Count WiFi connections
            wifi_count = session.run("MATCH ()-[r:CONNECTED_TO_WIFI]->() RETURN count(r) as count").single()['count']
            print(f"  📶 WiFi Connections: {wifi_count}")

            # Count CCTV detections
            cctv_count = session.run("MATCH ()-[r:DETECTED_IN]->() RETURN count(r) as count").single()['count']
            print(f"  📹 CCTV Detections: {cctv_count}")

            # Count library checkouts
            checkout_count = session.run("MATCH ()-[r:CHECKED_OUT_BOOK]->() RETURN count(r) as count").single()['count']
            print(f"  📚 Library Checkouts: {checkout_count}")

            # Count bookings
            booking_count = session.run("MATCH ()-[r:BOOKED_ROOM]->() RETURN count(r) as count").single()['count']
            print(f"  🔬 Lab Bookings: {booking_count}")

            # Count spatial activities
            spatial_count = session.run("MATCH (sa:SpatialActivity) RETURN count(sa) as count").single()['count']
            print(f"  📊 Spatial Activities: {spatial_count}")

            # Sample some entity activities
            print("\n  Sample Entity Activities:")
            sample = session.run("""
                MATCH (e:Entity)-[r]->(z:Zone)
                RETURN e.entity_id, e.name, e.role, type(r) as activity_type, z.zone_id
                LIMIT 5
            """)
            for rec in sample:
                print(f"    - {rec['e.entity_id']} ({rec['e.role']}): {rec['activity_type']} at {rec['z.zone_id']}")


def main():
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "Pressword@69"
    DATA_DIR = "/Users/dinokage/dev/fazri-analyzer/backend/augmented"

    try:
        with RealDataIngestion(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, DATA_DIR) as ingestion:
            success = ingestion.execute_ingestion()

            if success:
                print("\n✅ SUCCESS! Real data has been ingested into Neo4j")
                print("\nNow try these API endpoints:")
                print("• GET http://localhost:8000/api/v1/anomalies/detect")
                print("• GET http://localhost:8000/api/v1/anomalies/summary")
                print("• GET http://localhost:8000/api/v1/spatial/zones")
            else:
                print("\n❌ FAILED! Check logs above for errors")

    except Exception as e:
        print(f"\n💥 ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
