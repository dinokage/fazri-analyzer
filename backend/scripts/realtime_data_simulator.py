#!/usr/bin/env python3
"""
Real-time Data Simulator for FAZRI Analyzer

This script generates realistic campus activity data for demonstration purposes.
It simulates:
- Card swipes at various locations
- WiFi device associations
- Security alerts based on anomalies
- Entity movements across campus

Usage:
    python scripts/realtime_data_simulator.py [--interval SECONDS] [--alerts] [--movements] [--continuous]

Options:
    --interval SECONDS    Time between data generation cycles (default: 5)
    --alerts              Generate security alerts
    --movements           Generate movement/swipe data
    --continuous          Run continuously (Ctrl+C to stop)
    --burst               Generate a burst of activity (10 events at once)
"""

import sys
import os
import random
import argparse
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import csv
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override database host for local development (Docker uses postgres_db, local uses localhost)
if os.environ.get("LOCAL_DEV"):
    os.environ["POSTGRES_SERVER"] = "localhost"
    os.environ["NEO4J_URI"] = "neo4j://localhost:7687"
    os.environ["REDIS_HOST"] = "localhost"

from sqlalchemy.orm import Session
from neo4j import GraphDatabase
from database import SessionLocal, engine
from models.db.alerts import (
    Alert, AlertStatus, AlertSeverity, ActorType, StaffProfile
)
from models.schemas.alerts import AlertCreate, LocationSchema
from services.alerts import AlertService, AssignmentEngine
from config import settings


# ============================================================================
# CAMPUS CONFIGURATION
# ============================================================================

BUILDINGS = [
    "Main Library", "Engineering Block", "Science Complex", "Admin Building",
    "Student Center", "Computer Lab", "Research Wing", "Auditorium",
    "Cafeteria", "Sports Complex"
]

ZONES = {
    "LIB_ENT": {"name": "Library Entrance", "building": "Main Library", "floor": "G"},
    "LIB_1F": {"name": "Library Floor 1", "building": "Main Library", "floor": "1"},
    "LIB_2F": {"name": "Library Floor 2", "building": "Main Library", "floor": "2"},
    "ENG_LOBBY": {"name": "Engineering Lobby", "building": "Engineering Block", "floor": "G"},
    "ENG_LAB1": {"name": "Engineering Lab 1", "building": "Engineering Block", "floor": "1"},
    "ENG_LAB2": {"name": "Engineering Lab 2", "building": "Engineering Block", "floor": "2"},
    "SCI_ENT": {"name": "Science Entrance", "building": "Science Complex", "floor": "G"},
    "SCI_LAB": {"name": "Science Lab", "building": "Science Complex", "floor": "1"},
    "ADMIN_LOBBY": {"name": "Admin Lobby", "building": "Admin Building", "floor": "G"},
    "ADMIN_OFFICE": {"name": "Admin Office", "building": "Admin Building", "floor": "1"},
    "CAF_MAIN": {"name": "Main Cafeteria", "building": "Cafeteria", "floor": "G"},
    "COMP_LAB1": {"name": "Computer Lab 1", "building": "Computer Lab", "floor": "G"},
    "COMP_LAB2": {"name": "Computer Lab 2", "building": "Computer Lab", "floor": "1"},
    "AUD_MAIN": {"name": "Main Auditorium", "building": "Auditorium", "floor": "G"},
    "SPORTS_GYM": {"name": "Gymnasium", "building": "Sports Complex", "floor": "G"},
}

ACCESS_POINTS = [
    "AP_LIB_1", "AP_LIB_2", "AP_LIB_3", "AP_LIB_4", "AP_LIB_5",
    "AP_ENG_1", "AP_ENG_2", "AP_ENG_3", "AP_ENG_4", "AP_ENG_5",
    "AP_SCI_1", "AP_SCI_2", "AP_SCI_3",
    "AP_ADMIN_1", "AP_ADMIN_2",
    "AP_CAF_1", "AP_CAF_2", "AP_CAF_3", "AP_CAF_4",
    "AP_COMP_1", "AP_COMP_2", "AP_COMP_3",
    "AP_AUD_1", "AP_AUD_2", "AP_AUD_3",
    "AP_LAB_1", "AP_LAB_2", "AP_LAB_3", "AP_LAB_4",
]

ANOMALY_TYPES = [
    "unauthorized_access",
    "tailgating",
    "unusual_hours_access",
    "restricted_area_entry",
    "multiple_location_conflict",
    "device_anomaly",
    "access_pattern_deviation",
    "crowd_anomaly",
    "unattended_object",
]

ALERT_TEMPLATES = {
    "unauthorized_access": {
        "title": "Unauthorized Access Attempt Detected",
        "description": "An individual attempted to access a restricted area without proper credentials.",
        "severity": "high",
    },
    "tailgating": {
        "title": "Tailgating Incident Detected",
        "description": "Multiple individuals detected entering through a single card swipe event.",
        "severity": "medium",
    },
    "unusual_hours_access": {
        "title": "After-Hours Access Alert",
        "description": "Access detected outside normal operating hours.",
        "severity": "low",
    },
    "restricted_area_entry": {
        "title": "Restricted Zone Breach",
        "description": "Unauthorized entry into restricted research/admin area.",
        "severity": "critical",
    },
    "multiple_location_conflict": {
        "title": "Location Conflict Detected",
        "description": "Same credential detected at multiple locations simultaneously.",
        "severity": "high",
    },
    "device_anomaly": {
        "title": "Unknown Device Detected",
        "description": "Unregistered device connected to campus network.",
        "severity": "medium",
    },
    "access_pattern_deviation": {
        "title": "Unusual Access Pattern",
        "description": "Entity showing significant deviation from normal behavior patterns.",
        "severity": "medium",
    },
    "crowd_anomaly": {
        "title": "Unusual Crowd Gathering",
        "description": "Abnormal concentration of people detected in zone.",
        "severity": "high",
    },
    "unattended_object": {
        "title": "Unattended Object Alert",
        "description": "Suspicious unattended object detected in public area.",
        "severity": "critical",
    },
}


# ============================================================================
# NEO4J OCCUPANCY UPDATER
# ============================================================================

class Neo4jOccupancyUpdater:
    """Updates zone occupancy in Neo4j graph database"""

    def __init__(self):
        neo4j_uri = settings.NEO4J_URI
        neo4j_user = settings.NEO4J_USER
        neo4j_password = settings.NEO4J_PASSWORD
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self._zone_capacities = {}
        self._load_zone_capacities()

    def _load_zone_capacities(self):
        """Load zone capacities from Neo4j"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (z:Zone)
                    RETURN z.zone_id as zone_id, z.capacity as capacity
                """)
                for record in result:
                    self._zone_capacities[record["zone_id"]] = record["capacity"] or 100
        except Exception as e:
            print(f"Warning: Could not load zone capacities: {e}")
            # Use default capacities
            for zone_id in ZONES.keys():
                self._zone_capacities[zone_id] = 100

    def get_zone_ids(self) -> List[str]:
        """Get list of zone IDs from Neo4j"""
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (z:Zone) RETURN z.zone_id as zone_id")
                return [record["zone_id"] for record in result]
        except Exception as e:
            print(f"Warning: Could not get zone IDs: {e}")
            return list(ZONES.keys())

    def update_zone_occupancy(self, zone_id: str, occupancy_delta: int) -> Dict[str, Any]:
        """
        Update occupancy for a zone by creating a new SpatialActivity node.

        Args:
            zone_id: Zone identifier
            occupancy_delta: Change in occupancy (+1 for IN, -1 for OUT)

        Returns:
            Updated occupancy info
        """
        now = datetime.now()

        with self.driver.session() as session:
            # Get current occupancy from latest SpatialActivity
            result = session.run("""
                MATCH (z:Zone {zone_id: $zone_id})<-[:OCCURRED_IN]-(sa:SpatialActivity)
                WITH z, sa
                ORDER BY sa.timestamp DESC
                LIMIT 1
                RETURN sa.occupancy as current_occupancy, z.capacity as capacity
            """, zone_id=zone_id)

            record = result.single()
            if record:
                current = record["current_occupancy"] or 0
                capacity = record["capacity"] or 100
            else:
                current = random.randint(10, 50)  # Start with random baseline
                capacity = self._zone_capacities.get(zone_id, 100)

            # Calculate new occupancy (ensure it stays within bounds)
            new_occupancy = max(0, min(capacity + 20, current + occupancy_delta))

            # Create new SpatialActivity node
            session.run("""
                MATCH (z:Zone {zone_id: $zone_id})
                CREATE (sa:SpatialActivity {
                    timestamp: datetime($timestamp),
                    occupancy: $occupancy,
                    hour: $hour,
                    day_of_week: $day_of_week,
                    is_weekend: $is_weekend
                })-[:OCCURRED_IN]->(z)
            """,
                zone_id=zone_id,
                timestamp=now.isoformat(),
                occupancy=new_occupancy,
                hour=now.hour,
                day_of_week=now.isoweekday(),
                is_weekend=now.weekday() >= 5
            )

            return {
                "zone_id": zone_id,
                "previous_occupancy": current,
                "new_occupancy": new_occupancy,
                "capacity": capacity,
                "occupancy_rate": round(new_occupancy / capacity * 100, 1),
                "timestamp": now.isoformat()
            }

    def simulate_zone_activity(self, num_zones: int = 5) -> List[Dict[str, Any]]:
        """
        Simulate activity across multiple zones.

        Args:
            num_zones: Number of zones to update

        Returns:
            List of update results
        """
        zone_ids = self.get_zone_ids()
        if not zone_ids:
            zone_ids = list(ZONES.keys())

        results = []
        selected_zones = random.sample(zone_ids, min(num_zones, len(zone_ids)))

        for zone_id in selected_zones:
            # Simulate realistic movement patterns
            # More people entering during morning, leaving in evening
            hour = datetime.now().hour
            if 8 <= hour <= 12:  # Morning rush
                delta = random.choice([1, 1, 1, 2, 0])
            elif 12 <= hour <= 14:  # Lunch movement
                delta = random.choice([-1, 0, 1, -1, 1])
            elif 14 <= hour <= 17:  # Afternoon
                delta = random.choice([0, 1, -1, 0, 1])
            elif 17 <= hour <= 20:  # Evening exodus
                delta = random.choice([-1, -1, -2, 0, -1])
            else:  # Night/early morning
                delta = random.choice([0, 0, -1, 0, 1])

            result = self.update_zone_occupancy(zone_id, delta)
            results.append(result)

        return results

    def close(self):
        """Close the Neo4j driver"""
        self.driver.close()


# ============================================================================
# DATA LOADER
# ============================================================================

class CampusDataLoader:
    """Loads existing campus data from CSV files"""

    def __init__(self, data_dir: str = "augmented"):
        self.data_dir = data_dir
        self.entities: List[Dict] = []
        self.card_ids: List[str] = []
        self.device_hashes: List[str] = []
        self._load_profiles()

    def _load_profiles(self):
        """Load student/staff profiles"""
        profile_path = os.path.join(self.data_dir, "student_staff_profiles.csv")
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                reader = csv.DictReader(f)
                self.entities = list(reader)
                self.card_ids = [e['card_id'] for e in self.entities if e.get('card_id')]
                self.device_hashes = [e['device_hash'] for e in self.entities if e.get('device_hash')]
        else:
            # Generate dummy data if file doesn't exist
            print(f"Warning: {profile_path} not found. Using generated data.")
            self.card_ids = [f"C{i:04d}" for i in range(1000, 2000)]
            self.device_hashes = [f"DH{random.randbytes(6).hex()}" for _ in range(1000)]

    def get_random_entity(self) -> Dict:
        """Get a random entity from loaded data"""
        if self.entities:
            return random.choice(self.entities)
        return {
            "entity_id": f"E{random.randint(100000, 199999)}",
            "name": f"Person {random.randint(1, 1000)}",
            "card_id": random.choice(self.card_ids) if self.card_ids else f"C{random.randint(1000, 9999)}",
        }

    def get_random_card_id(self) -> str:
        return random.choice(self.card_ids) if self.card_ids else f"C{random.randint(1000, 9999)}"

    def get_random_device_hash(self) -> str:
        return random.choice(self.device_hashes) if self.device_hashes else f"DH{random.randbytes(6).hex()}"


# ============================================================================
# DATA GENERATORS
# ============================================================================

class CardSwipeGenerator:
    """Generates realistic card swipe events"""

    def __init__(self, data_loader: CampusDataLoader):
        self.data_loader = data_loader
        self.output_file = "augmented/campus_card_swipes_augmented.csv"

    def generate_swipe(self) -> Dict[str, Any]:
        """Generate a single card swipe event"""
        card_id = self.data_loader.get_random_card_id()
        zone_id = random.choice(list(ZONES.keys()))
        timestamp = datetime.now()
        direction = random.choice(["IN", "OUT"])

        return {
            "card_id": card_id,
            "location_id": zone_id,
            "timestamp": timestamp.isoformat(),
            "IN_OUT": direction,
        }

    def append_to_csv(self, swipe: Dict[str, Any]):
        """Append swipe to CSV file"""
        file_exists = os.path.exists(self.output_file)
        with open(self.output_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["card_id", "location_id", "timestamp", "IN_OUT"])
            if not file_exists:
                writer.writeheader()
            writer.writerow(swipe)

    def generate_batch(self, count: int = 5) -> List[Dict]:
        """Generate multiple swipe events"""
        swipes = []
        for _ in range(count):
            swipe = self.generate_swipe()
            swipes.append(swipe)
            self.append_to_csv(swipe)
        return swipes


class WiFiAssociationGenerator:
    """Generates WiFi association events"""

    def __init__(self, data_loader: CampusDataLoader):
        self.data_loader = data_loader
        self.output_file = "augmented/wifi_associations_logs_augmented.csv"

    def generate_association(self) -> Dict[str, Any]:
        """Generate a WiFi association event"""
        device_hash = self.data_loader.get_random_device_hash()
        ap_id = random.choice(ACCESS_POINTS)
        timestamp = datetime.now()

        return {
            "device_hash": device_hash,
            "ap_id": ap_id,
            "timestamp": timestamp.isoformat(),
        }

    def append_to_csv(self, assoc: Dict[str, Any]):
        """Append association to CSV file"""
        file_exists = os.path.exists(self.output_file)
        with open(self.output_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["device_hash", "ap_id", "timestamp"])
            if not file_exists:
                writer.writeheader()
            writer.writerow(assoc)

    def generate_batch(self, count: int = 5) -> List[Dict]:
        """Generate multiple WiFi associations"""
        associations = []
        for _ in range(count):
            assoc = self.generate_association()
            associations.append(assoc)
            self.append_to_csv(assoc)
        return associations


class AlertGenerator:
    """Generates security alerts via the API"""

    def __init__(self, db: Session, data_loader: CampusDataLoader):
        self.db = db
        self.data_loader = data_loader
        self.alert_service = AlertService(db)
        self.assignment_engine = AssignmentEngine(db)

    def generate_alert(self, anomaly_type: Optional[str] = None) -> Optional[Alert]:
        """Generate a security alert"""
        if anomaly_type is None:
            anomaly_type = random.choice(ANOMALY_TYPES)

        template = ALERT_TEMPLATES.get(anomaly_type, ALERT_TEMPLATES["unauthorized_access"])
        zone_id = random.choice(list(ZONES.keys()))
        zone_info = ZONES[zone_id]

        # Get random affected entities
        num_affected = random.randint(1, 3)
        affected_entities = []
        for _ in range(num_affected):
            entity = self.data_loader.get_random_entity()
            affected_entities.append(entity.get("entity_id", f"E{random.randint(100000, 199999)}"))

        # Create evidence based on anomaly type
        evidence = self._generate_evidence(anomaly_type, zone_id)

        alert_data = AlertCreate(
            title=template["title"],
            description=f"{template['description']} Location: {zone_info['name']}, {zone_info['building']}.",
            severity=template["severity"],
            location=LocationSchema(
                zone_id=zone_id,
                building=zone_info["building"],
                floor=zone_info["floor"],
            ),
            anomaly_type=anomaly_type,
            affected_entities=affected_entities,
            data_sources=random.sample(["card_swipe", "wifi_log", "cctv", "motion_sensor"], k=random.randint(1, 3)),
            evidence=evidence,
            is_mock=False,
        )

        try:
            alert = self.alert_service.create_alert(
                alert_data=alert_data,
                actor_type=ActorType.SYSTEM,
            )

            # Auto-assign the alert
            if alert.severity == AlertSeverity.CRITICAL:
                self.assignment_engine.assign_critical_alert(alert, max_assignees=3)
            else:
                self.assignment_engine.assign_alert(alert)

            self.db.refresh(alert)
            return alert

        except Exception as e:
            print(f"Error creating alert: {e}")
            return None

    def _generate_evidence(self, anomaly_type: str, zone_id: str) -> Dict[str, Any]:
        """Generate evidence data for an alert"""
        base_evidence = {
            "detection_time": datetime.now().isoformat(),
            "zone_id": zone_id,
            "confidence_score": round(random.uniform(0.75, 0.99), 2),
        }

        if anomaly_type == "unauthorized_access":
            base_evidence.update({
                "card_id": self.data_loader.get_random_card_id(),
                "access_level_required": random.choice(["admin", "staff", "restricted"]),
                "access_level_presented": "student",
            })
        elif anomaly_type == "tailgating":
            base_evidence.update({
                "persons_detected": random.randint(2, 4),
                "card_swipes": 1,
                "camera_id": f"CAM_{zone_id}_{random.randint(1, 5)}",
            })
        elif anomaly_type == "unusual_hours_access":
            base_evidence.update({
                "access_time": datetime.now().replace(hour=random.randint(0, 5)).isoformat(),
                "normal_hours": "08:00-22:00",
            })
        elif anomaly_type == "multiple_location_conflict":
            other_zone = random.choice([z for z in ZONES.keys() if z != zone_id])
            base_evidence.update({
                "location_1": zone_id,
                "location_2": other_zone,
                "time_difference_seconds": random.randint(1, 30),
            })
        elif anomaly_type == "crowd_anomaly":
            base_evidence.update({
                "current_occupancy": random.randint(80, 150),
                "normal_occupancy": random.randint(20, 40),
                "occupancy_threshold": 50,
            })

        return base_evidence


# ============================================================================
# MAIN SIMULATOR
# ============================================================================

class RealtimeSimulator:
    """Main simulator class that orchestrates data generation"""

    def __init__(self, db: Session):
        self.db = db
        self.data_loader = CampusDataLoader()
        self.swipe_generator = CardSwipeGenerator(self.data_loader)
        self.wifi_generator = WiFiAssociationGenerator(self.data_loader)
        self.alert_generator = AlertGenerator(db, self.data_loader)
        self.neo4j_updater = Neo4jOccupancyUpdater()

    def run_cycle(
        self,
        generate_movements: bool = True,
        generate_alerts: bool = True,
        generate_occupancy: bool = True,
        alert_probability: float = 0.3,
    ) -> Dict[str, Any]:
        """Run a single simulation cycle"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "card_swipes": [],
            "wifi_associations": [],
            "occupancy_updates": [],
            "alerts": [],
        }

        if generate_movements:
            # Generate card swipes (2-5 per cycle)
            num_swipes = random.randint(2, 5)
            swipes = self.swipe_generator.generate_batch(num_swipes)
            results["card_swipes"] = swipes

            # Generate WiFi associations (3-8 per cycle)
            num_wifi = random.randint(3, 8)
            associations = self.wifi_generator.generate_batch(num_wifi)
            results["wifi_associations"] = associations

        if generate_occupancy:
            # Update zone occupancies in Neo4j (3-7 zones per cycle)
            num_zones = random.randint(3, 7)
            try:
                occupancy_updates = self.neo4j_updater.simulate_zone_activity(num_zones)
                results["occupancy_updates"] = occupancy_updates
            except Exception as e:
                print(f"Error updating occupancy: {e}")

        if generate_alerts and random.random() < alert_probability:
            # Generate an alert
            alert = self.alert_generator.generate_alert()
            if alert:
                results["alerts"].append({
                    "id": str(alert.id),
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "zone": alert.location.get("zone_id"),
                })

        return results

    def run_burst(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate a burst of activity"""
        results = []
        for _ in range(count):
            result = self.run_cycle(
                generate_movements=True,
                generate_alerts=True,
                alert_probability=0.5,  # Higher probability for burst
            )
            results.append(result)
        return results


def main():
    parser = argparse.ArgumentParser(description="FAZRI Real-time Data Simulator")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between cycles")
    parser.add_argument("--alerts", action="store_true", help="Generate alerts")
    parser.add_argument("--movements", action="store_true", help="Generate movements/swipes")
    parser.add_argument("--occupancy", action="store_true", help="Generate occupancy updates (Neo4j)")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--burst", action="store_true", help="Generate burst of activity")
    parser.add_argument("--count", type=int, default=10, help="Number of events for burst mode")

    args = parser.parse_args()

    # Default to all if none specified
    if not args.alerts and not args.movements and not args.occupancy:
        args.alerts = True
        args.movements = True
        args.occupancy = True

    print("=" * 60)
    print("FAZRI Real-time Data Simulator")
    print("=" * 60)
    print(f"Mode: {'Continuous' if args.continuous else 'Single run'}")
    print(f"Interval: {args.interval}s")
    print(f"Generate Alerts: {args.alerts}")
    print(f"Generate Movements: {args.movements}")
    print(f"Generate Occupancy: {args.occupancy}")
    print("=" * 60)

    db = SessionLocal()
    try:
        simulator = RealtimeSimulator(db)

        if args.burst:
            print(f"\nGenerating burst of {args.count} events...")
            results = simulator.run_burst(args.count)
            for i, result in enumerate(results):
                print(f"\n[Event {i+1}]")
                print(f"  Card Swipes: {len(result['card_swipes'])}")
                print(f"  WiFi Associations: {len(result['wifi_associations'])}")
                if result['alerts']:
                    for alert in result['alerts']:
                        print(f"  Alert: {alert['title']} ({alert['severity']})")
            print(f"\nBurst complete! Generated {args.count} events.")

        elif args.continuous:
            print("\nRunning continuously. Press Ctrl+C to stop.\n")
            cycle = 0
            try:
                while True:
                    cycle += 1
                    result = simulator.run_cycle(
                        generate_movements=args.movements,
                        generate_alerts=args.alerts,
                        generate_occupancy=args.occupancy,
                    )

                    print(f"[Cycle {cycle}] {result['timestamp']}")
                    print(f"  Swipes: {len(result['card_swipes'])} | WiFi: {len(result['wifi_associations'])} | Occupancy Updates: {len(result.get('occupancy_updates', []))}")
                    if result.get('occupancy_updates'):
                        for update in result['occupancy_updates'][:3]:  # Show first 3
                            print(f"    📊 {update['zone_id']}: {update['new_occupancy']}/{update['capacity']} ({update['occupancy_rate']}%)")
                    if result['alerts']:
                        for alert in result['alerts']:
                            print(f"  🚨 ALERT: {alert['title']} ({alert['severity'].upper()})")

                    time.sleep(args.interval)

            except KeyboardInterrupt:
                print("\n\nSimulation stopped by user.")

        else:
            # Single run
            result = simulator.run_cycle(
                generate_movements=args.movements,
                generate_alerts=args.alerts,
                generate_occupancy=args.occupancy,
                alert_probability=0.8,  # Higher probability for single run demo
            )

            print(f"\nGenerated at {result['timestamp']}:")
            print(f"  Card Swipes: {len(result['card_swipes'])}")
            for swipe in result['card_swipes']:
                print(f"    - {swipe['card_id']} @ {swipe['location_id']} ({swipe['IN_OUT']})")

            print(f"  WiFi Associations: {len(result['wifi_associations'])}")
            for assoc in result['wifi_associations']:
                print(f"    - {assoc['device_hash'][:12]}... @ {assoc['ap_id']}")

            if result.get('occupancy_updates'):
                print(f"  Occupancy Updates: {len(result['occupancy_updates'])}")
                for update in result['occupancy_updates']:
                    status = "🔴" if update['occupancy_rate'] > 80 else "🟡" if update['occupancy_rate'] > 50 else "🟢"
                    print(f"    {status} {update['zone_id']}: {update['previous_occupancy']} → {update['new_occupancy']} ({update['occupancy_rate']}%)")

            if result['alerts']:
                print(f"  Alerts Generated:")
                for alert in result['alerts']:
                    print(f"    🚨 {alert['title']}")
                    print(f"       Severity: {alert['severity']} | Zone: {alert['zone']}")
            else:
                print("  No alerts generated this cycle.")

    finally:
        db.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
