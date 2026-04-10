# backend/data/zones_sample_data.py
from datetime import datetime

ZONES_DATA = [
    {
        "zone_id": "ADMIN_LOBBY",
        "name": "Administrative Block Lobby",
        "zone_type": "LOBBY",
        "capacity": 50,
        "building": "Administrative Block",
        "floor": 1,
        "coordinates": {"lat": 26.1445, "lng": 91.7362},
        "description": "Main entrance lobby for administrative offices",
        "operating_hours": {"start": "08:00", "end": "18:00"},
        "access_level": "PUBLIC",
        "facilities": ["reception_desk", "seating_area", "information_board"],
        "peak_hours": [9, 10, 14, 15, 16, 17],  # Typical busy hours
        "department": "Administration",
        "zone_category": "COMMON_AREA"
    },
    {
        "zone_id": "AUDITORIUM",
        "name": "Main Auditorium",
        "zone_type": "AUDITORIUM",
        "capacity": 300,
        "building": "Academic Block B",
        "floor": 1,
        "coordinates": {"lat": 26.1448, "lng": 91.7365},
        "description": "Large auditorium for events, seminars, and presentations",
        "operating_hours": {"start": "09:00", "end": "22:00"},
        "access_level": "RESTRICTED",
        "facilities": ["stage", "projector", "sound_system", "ac", "recording_equipment"],
        "peak_hours": [10, 11, 14, 15, 19, 20],
        "department": "Events",
        "zone_category": "EVENT_SPACE"
    },
    {
        "zone_id": "CAF_01",
        "name": "Central Cafeteria",
        "zone_type": "CAFETERIA",
        "capacity": 200,
        "building": "Student Center",
        "floor": 1,
        "coordinates": {"lat": 26.1440, "lng": 91.7360},
        "description": "Main dining area for students and staff",
        "operating_hours": {"start": "07:00", "end": "22:00"},
        "access_level": "PUBLIC",
        "facilities": ["dining_tables", "food_counters", "vending_machines", "microwave", "water_dispensers"],
        "peak_hours": [8, 9, 12, 13, 14, 19, 20],  # Breakfast, lunch, dinner times
        "department": "Food Services",
        "zone_category": "DINING"
    },
    {
        "zone_id": "GYM",
        "name": "Fitness Center",
        "zone_type": "GYM",
        "capacity": 80,
        "building": "Sports Complex",
        "floor": 1,
        "coordinates": {"lat": 26.1435, "lng": 91.7355},
        "description": "Main gymnasium with fitness equipment and sports facilities",
        "operating_hours": {"start": "06:00", "end": "22:00"},
        "access_level": "MEMBERSHIP_REQUIRED",
        "facilities": ["cardio_equipment", "weight_machines", "free_weights", "locker_rooms", "shower_facilities"],
        "peak_hours": [6, 7, 17, 18, 19, 20, 21],  # Early morning and evening
        "department": "Sports",
        "zone_category": "RECREATION"
    },
    {
        "zone_id": "HOSTEL_GATE",
        "name": "Hostel Main Gate",
        "zone_type": "ENTRANCE",
        "capacity": 25,
        "building": "Hostel Block A",
        "floor": 0,  # Ground level
        "coordinates": {"lat": 26.1450, "lng": 91.7370},
        "description": "Security checkpoint and entrance to hostel premises",
        "operating_hours": {"start": "00:00", "end": "23:59"},  # 24/7
        "access_level": "RESTRICTED",
        "facilities": ["security_booth", "id_scanner", "cctv", "barrier_gate"],
        "peak_hours": [7, 8, 17, 18, 19, 20, 21, 22],  # Entry/exit times
        "department": "Security",
        "zone_category": "SECURITY_CHECKPOINT"
    },
    {
        "zone_id": "LAB_101",
        "name": "Computer Science Lab 101",
        "zone_type": "LAB",
        "capacity": 40,
        "building": "Academic Block A",
        "floor": 1,
        "coordinates": {"lat": 26.1442, "lng": 91.7358},
        "description": "Programming and software development laboratory",
        "operating_hours": {"start": "08:00", "end": "20:00"},
        "access_level": "STUDENT_FACULTY",
        "facilities": ["computers_40", "projector", "whiteboard", "ac", "network_switches"],
        "peak_hours": [9, 10, 11, 14, 15, 16, 17],  # Class hours
        "department": "Computer Science",
        "zone_category": "ACADEMIC_LAB",
        "lab_type": "COMPUTER_LAB",
        "equipment_count": 40
    },
    {
        "zone_id": "LAB_306",
        "name": "Electronics Lab 306",
        "zone_type": "LAB",
        "capacity": 30,
        "building": "Engineering Block",
        "floor": 3,
        "coordinates": {"lat": 26.1447, "lng": 91.7368},
        "description": "Electronics and circuit design laboratory",
        "operating_hours": {"start": "08:00", "end": "18:00"},
        "access_level": "STUDENT_FACULTY",
        "facilities": ["workbenches_15", "oscilloscopes", "function_generators", "multimeters", "power_supplies", "component_storage"],
        "peak_hours": [10, 11, 14, 15, 16],
        "department": "Electronics Engineering",
        "zone_category": "ACADEMIC_LAB",
        "lab_type": "ELECTRONICS_LAB",
        "equipment_count": 15,
        "safety_requirements": ["safety_goggles", "grounding_straps"]
    },
    {
        "zone_id": "LIB_ENT",
        "name": "Library Main Entrance",
        "zone_type": "ENTRANCE",
        "capacity": 20,
        "building": "Library Building",
        "floor": 1,
        "coordinates": {"lat": 26.1443, "lng": 91.7363},
        "description": "Main entrance and security checkpoint for library",
        "operating_hours": {"start": "08:00", "end": "22:00"},
        "access_level": "STUDENT_FACULTY",
        "facilities": ["security_desk", "id_scanner", "book_scanner", "turnstiles"],
        "peak_hours": [9, 10, 11, 14, 15, 16, 17, 18, 19],  # Study hours
        "department": "Library Services",
        "zone_category": "LIBRARY_ACCESS"
    }
]

# Additional metadata for enhanced functionality
ZONE_RELATIONSHIPS = [
    {
        "source_zone": "ADMIN_LOBBY",
        "target_zone": "LIB_ENT",
        "relationship_type": "WALKING_DISTANCE",
        "distance_meters": 150,
        "walking_time_minutes": 2
    },
    {
        "source_zone": "CAF_01",
        "target_zone": "LAB_101",
        "relationship_type": "WALKING_DISTANCE",
        "distance_meters": 200,
        "walking_time_minutes": 3
    },
    {
        "source_zone": "LAB_101",
        "target_zone": "LAB_306",
        "relationship_type": "WALKING_DISTANCE",
        "distance_meters": 300,
        "walking_time_minutes": 4
    },
    {
        "source_zone": "GYM",
        "target_zone": "HOSTEL_GATE",
        "relationship_type": "WALKING_DISTANCE",
        "distance_meters": 250,
        "walking_time_minutes": 3
    }
]

# Sample historical occupancy patterns for training your ML models
SAMPLE_OCCUPANCY_PATTERNS = {
    "ADMIN_LOBBY": {
        "weekday_pattern": {
            8: 15, 9: 35, 10: 40, 11: 30, 12: 25, 13: 20, 14: 35, 15: 45, 16: 40, 17: 35, 18: 10
        },
        "weekend_pattern": {
            9: 5, 10: 8, 11: 6, 12: 4, 13: 3, 14: 5, 15: 7, 16: 6, 17: 4
        }
    },
    "AUDITORIUM": {
        "weekday_pattern": {
            9: 0, 10: 150, 11: 280, 12: 0, 13: 0, 14: 200, 15: 250, 16: 0, 17: 0, 19: 180, 20: 220
        },
        "weekend_pattern": {
            10: 0, 14: 100, 15: 150, 19: 200, 20: 180
        }
    },
    "CAF_01": {
        "weekday_pattern": {
            7: 20, 8: 80, 9: 120, 10: 40, 11: 60, 12: 150, 13: 180, 14: 160, 15: 50, 16: 30, 17: 40, 18: 60, 19: 140, 20: 120, 21: 60
        },
        "weekend_pattern": {
            8: 30, 9: 60, 10: 80, 11: 70, 12: 120, 13: 140, 14: 100, 18: 80, 19: 100, 20: 90
        }
    },
    "GYM": {
        "weekday_pattern": {
            6: 25, 7: 45, 8: 35, 9: 15, 10: 10, 17: 50, 18: 70, 19: 65, 20: 55, 21: 40, 22: 20
        },
        "weekend_pattern": {
            7: 20, 8: 30, 9: 40, 10: 45, 11: 35, 17: 40, 18: 50, 19: 45, 20: 35, 21: 25
        }
    },
    "HOSTEL_GATE": {
        "weekday_pattern": {
            7: 15, 8: 20, 9: 12, 10: 5, 17: 18, 18: 22, 19: 20, 20: 18, 21: 15, 22: 12
        },
        "weekend_pattern": {
            8: 10, 9: 12, 10: 8, 11: 6, 18: 15, 19: 18, 20: 16, 21: 12, 22: 10
        }
    },
    "LAB_101": {
        "weekday_pattern": {
            8: 5, 9: 35, 10: 38, 11: 40, 12: 15, 13: 8, 14: 32, 15: 35, 16: 38, 17: 30, 18: 15, 19: 10, 20: 5
        },
        "weekend_pattern": {
            10: 8, 11: 12, 14: 15, 15: 18, 16: 12, 17: 8
        }
    },
    "LAB_306": {
        "weekday_pattern": {
            8: 3, 9: 8, 10: 25, 11: 28, 12: 12, 13: 5, 14: 22, 15: 26, 16: 24, 17: 15, 18: 8
        },
        "weekend_pattern": {
            10: 5, 11: 8, 14: 10, 15: 12, 16: 8
        }
    },
    "LIB_ENT": {
        "weekday_pattern": {
            8: 8, 9: 15, 10: 18, 11: 16, 12: 12, 13: 10, 14: 16, 15: 18, 16: 20, 17: 18, 18: 16, 19: 14, 20: 12, 21: 8, 22: 5
        },
        "weekend_pattern": {
            9: 6, 10: 10, 11: 12, 12: 8, 14: 12, 15: 15, 16: 14, 17: 12, 18: 10, 19: 8, 20: 6
        }
    }
}

# Zone configuration for different scenarios
ZONE_CONFIGURATIONS = {
    "emergency_capacity": {
        "ADMIN_LOBBY": 25,  # 50% capacity during emergencies
        "AUDITORIUM": 150,
        "CAF_01": 100,
        "GYM": 40,
        "HOSTEL_GATE": 15,
        "LAB_101": 20,
        "LAB_306": 15,
        "LIB_ENT": 10
    },
    "covid_capacity": {
        "ADMIN_LOBBY": 17,  # 33% capacity for social distancing
        "AUDITORIUM": 100,
        "CAF_01": 67,
        "GYM": 27,
        "HOSTEL_GATE": 8,
        "LAB_101": 13,
        "LAB_306": 10,
        "LIB_ENT": 7
    }
}

# Function to initialize zones in Neo4j
def initialize_zones_in_neo4j(spatial_service):
    """Initialize all zones with sample data"""
    
    # Create zone nodes
    spatial_service.neo4j.create_zone_nodes(ZONES_DATA)
    
    # Create relationships between zones
    with spatial_service.neo4j.driver.session() as session:
        for rel in ZONE_RELATIONSHIPS:
            session.run("""
                MATCH (z1:Zone {zone_id: $source_zone})
                MATCH (z2:Zone {zone_id: $target_zone})
                CREATE (z1)-[:CONNECTED_TO {
                    relationship_type: $relationship_type,
                    distance_meters: $distance_meters,
                    walking_time_minutes: $walking_time_minutes
                }]->(z2)
            """, rel)
    
    print("Zones initialized successfully!")
    return True

# Function to generate synthetic historical data for training
def generate_synthetic_historical_data(spatial_service, days_back=30):
    """Generate synthetic historical occupancy data for ML training"""
    from datetime import datetime, timedelta
    import random
    
    with spatial_service.neo4j.driver.session() as session:
        for zone_id, patterns in SAMPLE_OCCUPANCY_PATTERNS.items():
            for day in range(days_back):
                date = datetime.now() - timedelta(days=day)
                is_weekend = date.weekday() >= 5
                
                pattern = patterns["weekend_pattern"] if is_weekend else patterns["weekday_pattern"]
                
                for hour, base_occupancy in pattern.items():
                    # Add some randomness to make it realistic
                    actual_occupancy = max(0, base_occupancy + random.randint(-5, 5))
                    
                    # Create synthetic activity record
                    timestamp = date.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
                    
                    session.run("""
                        MERGE (z:Zone {zone_id: $zone_id})
                        CREATE (a:SyntheticActivity {
                            timestamp: datetime($timestamp),
                            occupancy: $occupancy,
                            hour: $hour,
                            day_of_week: $day_of_week,
                            is_weekend: $is_weekend
                        })
                        CREATE (a)-[:OCCURRED_IN]->(z)
                    """, {
                        'zone_id': zone_id,
                        'timestamp': timestamp.isoformat(),
                        'occupancy': actual_occupancy,
                        'hour': hour,
                        'day_of_week': date.weekday() + 1,
                        'is_weekend': is_weekend
                    })
    
    print(f"Generated {days_back} days of synthetic historical data!")
    return True

# Usage example
if __name__ == "__main__":
    # This would be called from your main application
    print("Sample zones data prepared!")
    print(f"Total zones: {len(ZONES_DATA)}")
    print("Zone types:", set(zone['zone_type'] for zone in ZONES_DATA))
    print("Departments:", set(zone['department'] for zone in ZONES_DATA))