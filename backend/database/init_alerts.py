"""
Database initialization script for the Alert System.
Creates tables and seeds demo scenarios.
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from database.connection import engine, SessionLocal, Base
from models.db.alerts import (
    Alert,
    AlertAssignment,
    AlertAuditLog,
    StaffProfile,
    StaffLocation,
    NotificationQueue,
    NotificationLog,
    DemoScenario,
    DemoTimelineEvent,
    AlertSeverity,
    StaffRole,
)

logger = logging.getLogger(__name__)


def create_tables():
    """Create all alert system tables"""
    logger.info("Creating alert system tables...")

    # Import models to register them with Base
    from models.db import alerts  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Alert system tables created successfully")


def seed_demo_scenarios(db: Session):
    """Seed the demo scenarios from ALERTS.md specification"""

    # Check if scenarios already exist
    existing = db.query(DemoScenario).count()
    if existing > 0:
        logger.info(f"Demo scenarios already exist ({existing} found), skipping seed")
        return

    logger.info("Seeding demo scenarios...")

    scenarios = [
        # Scenario 1: Unauthorized Access Attempt
        {
            "id": "unauthorized_access",
            "name": "Unauthorized Access Attempt",
            "description": "Multiple failed card swipe attempts at restricted lab after hours",
            "severity": AlertSeverity.MEDIUM,
            "duration_seconds": 45,
            "auto_advance": True,
            "default_speed": 1.0,
            "display_order": 1,
            "alert_template": {
                "title": "Unusual Access Pattern Detected",
                "description": "5 failed card swipe attempts detected at Lab 301 entrance within 2 minutes. Last successful swipe at this location was 6 hours ago.",
                "location": {
                    "zone_id": "LAB_305",
                    "building": "Science Building A",
                    "floor": "3",
                    "coordinates": {"lat": 26.1912, "lng": 91.6985}
                },
                "affected_entities": ["student_12345"],
                "data_sources": ["CARD_SWIPE"],
                "evidence": {
                    "failed_attempts": 5,
                    "time_window": "23:15 - 23:17",
                    "card_holder": "Dr. Sarah Chen",
                    "access_history": "Normal pattern: Mon-Fri 09:00-17:00"
                }
            },
            "timeline_events": [
                {"step_number": 1, "delay_seconds": 0, "action": "create", "description": "Alert created", "action_data": {}, "narration_text": "Our AI has detected unusual card swipe patterns at a restricted lab after hours."},
                {"step_number": 2, "delay_seconds": 5, "action": "assign", "description": "Auto-assigned to Officer Johnson", "action_data": {"staff_name": "Officer Johnson", "staff_role": "security"}, "narration_text": "Within seconds, the system automatically assigns the nearest available security officer."},
                {"step_number": 3, "delay_seconds": 10, "action": "acknowledge", "description": "Officer Johnson acknowledges alert", "action_data": {}, "narration_text": "Officer Johnson receives an instant push notification and acknowledges the alert."},
                {"step_number": 4, "delay_seconds": 15, "action": "status_change", "description": "Status updates to Investigating", "action_data": {"new_status": "investigating"}, "narration_text": "The officer updates their status to investigating and heads to the location."},
                {"step_number": 5, "delay_seconds": 30, "action": "note_add", "description": "Officer arrives at location", "action_data": {"note": "At location, investigating"}, "narration_text": "Officer arrives at the scene and begins investigation."},
                {"step_number": 6, "delay_seconds": 45, "action": "resolve", "description": "Resolved as False Alarm", "action_data": {"resolution_type": "false_alarm", "notes": "Authorized researcher with wrong card"}, "narration_text": "Case resolved - it was an authorized researcher using the wrong access card."}
            ]
        },
        # Scenario 2: Suspicious Loitering
        {
            "id": "suspicious_loitering",
            "name": "Suspicious Loitering",
            "description": "Unidentified person detected in restricted area for extended period",
            "severity": AlertSeverity.HIGH,
            "duration_seconds": 50,
            "auto_advance": True,
            "default_speed": 1.0,
            "display_order": 2,
            "alert_template": {
                "title": "Suspicious Activity - Restricted Area",
                "description": "Person detected in restricted server room corridor for 15+ minutes. No valid card swipes in area. Face recognition: No match in database.",
                "location": {
                    "zone_id": "ADMIN_LOBBY",
                    "building": "Engineering Complex",
                    "floor": "Basement",
                    "coordinates": {"lat": 26.1920, "lng": 91.6990}
                },
                "affected_entities": ["unknown_person_001"],
                "data_sources": ["CCTV", "CARD_SWIPE"],
                "evidence": {
                    "duration": "15 minutes 32 seconds",
                    "last_valid_swipe": "None in last 2 hours",
                    "face_recognition": "No match",
                    "movement_pattern": "Back and forth near server room door",
                    "cctv_frames": ["frame_001.jpg", "frame_002.jpg", "frame_003.jpg"]
                }
            },
            "timeline_events": [
                {"step_number": 1, "delay_seconds": 0, "action": "create", "description": "Alert created", "action_data": {}, "narration_text": "Suspicious activity detected in a restricted area."},
                {"step_number": 2, "delay_seconds": 3, "action": "assign", "description": "Auto-assigned to Supervisor Rodriguez", "action_data": {"staff_name": "Supervisor Rodriguez", "staff_role": "supervisor"}, "narration_text": "High severity alert - assigned to Security Supervisor."},
                {"step_number": 3, "delay_seconds": 8, "action": "acknowledge", "description": "Supervisor Rodriguez acknowledges", "action_data": {}, "narration_text": "Supervisor acknowledges and takes command of the response."},
                {"step_number": 4, "delay_seconds": 12, "action": "status_change", "description": "Status updates to Investigating", "action_data": {"new_status": "investigating"}, "narration_text": "Investigation begins with live CCTV monitoring."},
                {"step_number": 5, "delay_seconds": 20, "action": "backup_request", "description": "Backup requested - Officer Martinez assigned", "action_data": {"staff_name": "Officer Martinez", "staff_role": "security"}, "narration_text": "Supervisor requests backup for the restricted area."},
                {"step_number": 6, "delay_seconds": 35, "action": "note_add", "description": "Both officers at location", "action_data": {"note": "Both officers on scene"}, "narration_text": "Both officers arrive and secure the area."},
                {"step_number": 7, "delay_seconds": 50, "action": "resolve", "description": "Resolved - Visitor escorted out", "action_data": {"resolution_type": "resolved", "notes": "Visitor escorted out - updated access protocols"}, "narration_text": "Situation resolved - visitor escorted out and access protocols updated."}
            ]
        },
        # Scenario 3: Multiple Coordinated Anomalies
        {
            "id": "coordinated_activity",
            "name": "Multiple Coordinated Anomalies",
            "description": "Coordinated unusual activity across multiple locations",
            "severity": AlertSeverity.CRITICAL,
            "duration_seconds": 40,
            "auto_advance": True,
            "default_speed": 1.0,
            "display_order": 3,
            "alert_template": {
                "title": "Multiple Coordinated Anomalies Detected",
                "description": "Simultaneous unusual WiFi activity + abnormal movement patterns detected across 4 buildings. Pattern suggests coordinated activity. Confidence: 87%",
                "location": {
                    "zone_id": "CAMPUS_WIDE",
                    "building": "Multiple Buildings",
                    "floor": "Various",
                    "coordinates": {"lat": 26.1915, "lng": 91.6988}
                },
                "affected_entities": ["entity_001", "entity_002", "entity_003", "entity_004"],
                "data_sources": ["WIFI", "CCTV", "CARD_SWIPE"],
                "evidence": {
                    "affected_buildings": ["LIB_ENT", "CAF_01", "ADMIN_LOBBY", "LAB_101"],
                    "unusual_wifi_devices": 15,
                    "movement_correlation": "High (0.87)",
                    "time_correlation": "Simultaneous within 30 seconds",
                    "ai_confidence": 0.87
                }
            },
            "timeline_events": [
                {"step_number": 1, "delay_seconds": 0, "action": "create", "description": "Critical alert created", "action_data": {}, "narration_text": "CRITICAL: Multiple coordinated anomalies detected across campus!"},
                {"step_number": 2, "delay_seconds": 2, "action": "escalate", "description": "Escalated to Security Chief", "action_data": {"staff_name": "Security Chief Williams", "staff_role": "admin"}, "narration_text": "Critical severity triggers immediate escalation to Security Chief."},
                {"step_number": 3, "delay_seconds": 3, "action": "multi_assign", "description": "3 security staff assigned simultaneously", "action_data": {"staff_names": ["Officer Johnson", "Officer Martinez", "Officer Brown"]}, "narration_text": "Multiple staff assigned to cover all affected locations."},
                {"step_number": 4, "delay_seconds": 7, "action": "acknowledge", "description": "All staff acknowledge", "action_data": {}, "narration_text": "All assigned personnel acknowledge and mobilize."},
                {"step_number": 5, "delay_seconds": 10, "action": "status_change", "description": "Security Chief views live CCTV", "action_data": {"new_status": "investigating", "note": "Live monitoring active"}, "narration_text": "Security Chief monitors all locations via live CCTV feeds."},
                {"step_number": 6, "delay_seconds": 25, "action": "note_add", "description": "All locations secured", "action_data": {"note": "All locations secured - Fire drill miscommunication"}, "narration_text": "All locations secured - cause identified."},
                {"step_number": 7, "delay_seconds": 40, "action": "resolve", "description": "Resolved with incident report", "action_data": {"resolution_type": "false_alarm", "notes": "Fire drill miscommunication - all clear"}, "narration_text": "Incident resolved - was an unannounced fire drill exercise."}
            ]
        },
        # Scenario 4: After-Hours Equipment Access
        {
            "id": "after_hours_equipment",
            "name": "After-Hours Equipment Access",
            "description": "Lab equipment usage detected outside normal hours",
            "severity": AlertSeverity.LOW,
            "duration_seconds": 90,
            "auto_advance": True,
            "default_speed": 2.0,
            "display_order": 4,
            "alert_template": {
                "title": "Unusual Lab Equipment Usage",
                "description": "High-power centrifuge activated at 02:30 AM. Typical usage hours: 08:00-18:00. No card swipe detected within 15 minutes of activation.",
                "location": {
                    "zone_id": "LAB_102",
                    "building": "Research Lab Building",
                    "floor": "2",
                    "coordinates": {"lat": 26.1918, "lng": 91.6992}
                },
                "affected_entities": ["equipment_centrifuge_204"],
                "data_sources": ["IOT_SENSOR", "CARD_SWIPE"],
                "evidence": {
                    "equipment_id": "CENT-204-A",
                    "activation_time": "02:30:15",
                    "last_card_swipe": "02:15:00 - Student ID 67890",
                    "usage_pattern": "First after-hours use in 3 months",
                    "power_consumption": "Normal range"
                }
            },
            "timeline_events": [
                {"step_number": 1, "delay_seconds": 0, "action": "create", "description": "Alert created", "action_data": {}, "narration_text": "Unusual lab equipment usage detected after hours."},
                {"step_number": 2, "delay_seconds": 15, "action": "assign", "description": "Auto-assigned to Dr. Kim", "action_data": {"staff_name": "Dr. Kim", "staff_role": "lab_supervisor"}, "narration_text": "Low severity - assigned to Lab Supervisor for review."},
                {"step_number": 3, "delay_seconds": 45, "action": "acknowledge", "description": "Dr. Kim acknowledges from mobile", "action_data": {}, "narration_text": "Dr. Kim acknowledges remotely and checks equipment logs."},
                {"step_number": 4, "delay_seconds": 60, "action": "note_add", "description": "Checks equipment logs remotely", "action_data": {"note": "Reviewing remote access logs"}, "narration_text": "Equipment logs reviewed - authorized user identified."},
                {"step_number": 5, "delay_seconds": 90, "action": "resolve", "description": "Resolved - PhD student with permission", "action_data": {"resolution_type": "no_action_required", "notes": "Authorized - PhD student with after-hours permission"}, "narration_text": "Verified - PhD student had pre-approved after-hours access."}
            ]
        },
        # Scenario 5: Escalation Flow Demo
        {
            "id": "escalation_demo",
            "name": "Escalation Flow Demo",
            "description": "Unacknowledged alert escalates through chain of command",
            "severity": AlertSeverity.HIGH,
            "duration_seconds": 900,
            "auto_advance": False,
            "default_speed": 10.0,
            "display_order": 5,
            "alert_template": {
                "title": "Unattended Bag in Public Area",
                "description": "Backpack left unattended in busy lobby area for 20+ minutes. No person in vicinity. Object detection confidence: 92%",
                "location": {
                    "zone_id": "CAF_01",
                    "building": "Student Union",
                    "floor": "1",
                    "coordinates": {"lat": 26.1922, "lng": 91.6995}
                },
                "affected_entities": ["object_unattended_001"],
                "data_sources": ["CCTV"],
                "evidence": {
                    "unattended_duration": "20 minutes 15 seconds",
                    "last_person_nearby": "18 minutes ago",
                    "object_type": "Backpack (92% confidence)",
                    "size": "Medium (estimated 15-20L)",
                    "video_clip": "union_lobby_camera3_segment.mp4"
                }
            },
            "timeline_events": [
                {"step_number": 1, "delay_seconds": 0, "action": "create", "description": "Alert created", "action_data": {}, "narration_text": "Unattended bag detected in busy public area."},
                {"step_number": 2, "delay_seconds": 5, "action": "assign", "description": "Auto-assigned to Officer Brown", "action_data": {"staff_name": "Officer Brown", "staff_role": "security"}, "narration_text": "Alert assigned to nearest security officer."},
                {"step_number": 3, "delay_seconds": 300, "action": "escalate", "description": "No acknowledgment - Escalated to Supervisor", "action_data": {"reason": "No acknowledgment after 5 minutes", "new_assignee": "Supervisor Lopez"}, "narration_text": "Officer Brown hasn't responded - auto-escalating to Supervisor."},
                {"step_number": 4, "delay_seconds": 360, "action": "acknowledge", "description": "Supervisor Lopez acknowledges and takes over", "action_data": {}, "narration_text": "Supervisor Lopez takes command of the response."},
                {"step_number": 5, "delay_seconds": 420, "action": "note_add", "description": "Supervisor requests assessment", "action_data": {"note": "Requesting bomb squad assessment"}, "narration_text": "Supervisor requests specialized assessment."},
                {"step_number": 6, "delay_seconds": 600, "action": "severity_change", "description": "Updated to CRITICAL severity", "action_data": {"new_severity": "critical"}, "narration_text": "Severity upgraded to CRITICAL based on assessment."},
                {"step_number": 7, "delay_seconds": 900, "action": "resolve", "description": "Resolved - Student backpack identified", "action_data": {"resolution_type": "false_alarm", "notes": "Student backpack - owner located and identified"}, "narration_text": "Resolved - owner found, just forgot their backpack while studying."}
            ]
        }
    ]

    for scenario_data in scenarios:
        timeline_events = scenario_data.pop("timeline_events")

        # Create scenario
        scenario = DemoScenario(**scenario_data)
        db.add(scenario)
        db.flush()

        # Create timeline events
        for event_data in timeline_events:
            event = DemoTimelineEvent(
                scenario_id=scenario.id,
                **event_data
            )
            db.add(event)

    db.commit()
    logger.info(f"Seeded {len(scenarios)} demo scenarios")


def seed_demo_staff(db: Session):
    """Seed demo staff accounts"""

    # Check if demo staff already exist
    existing = db.query(StaffProfile).filter(StaffProfile.is_mock_user == True).count()
    if existing > 0:
        logger.info(f"Demo staff already exist ({existing} found), skipping seed")
        return

    logger.info("Seeding demo staff accounts...")

    demo_staff = [
        {
            "name": "Officer Johnson",
            "email": "johnson@demo.fazri.com",
            "phone": "+1-555-0101",
            "role": StaffRole.SECURITY,
            "department": "Campus Security",
            "on_duty": True,
            "max_concurrent_assignments": 3,
            "contact_preferences": {"email": True, "sms": True, "push": True},
            "is_mock_user": True,
        },
        {
            "name": "Supervisor Rodriguez",
            "email": "rodriguez@demo.fazri.com",
            "phone": "+1-555-0102",
            "role": StaffRole.SUPERVISOR,
            "department": "Campus Security",
            "on_duty": True,
            "max_concurrent_assignments": 5,
            "contact_preferences": {"email": True, "sms": True, "push": True},
            "is_mock_user": True,
        },
        {
            "name": "Officer Martinez",
            "email": "martinez@demo.fazri.com",
            "phone": "+1-555-0103",
            "role": StaffRole.SECURITY,
            "department": "Campus Security",
            "on_duty": True,
            "max_concurrent_assignments": 3,
            "contact_preferences": {"email": True, "sms": True, "push": True},
            "is_mock_user": True,
        },
        {
            "name": "Security Chief Williams",
            "email": "williams@demo.fazri.com",
            "phone": "+1-555-0104",
            "role": StaffRole.ADMIN,
            "department": "Campus Security",
            "on_duty": True,
            "max_concurrent_assignments": 10,
            "contact_preferences": {"email": True, "sms": True, "push": True},
            "is_mock_user": True,
        },
        {
            "name": "Dr. Kim",
            "email": "kim@demo.fazri.com",
            "phone": "+1-555-0105",
            "role": StaffRole.LAB_SUPERVISOR,
            "department": "Research Labs",
            "on_duty": True,
            "max_concurrent_assignments": 2,
            "contact_preferences": {"email": True, "sms": False, "push": True},
            "is_mock_user": True,
        },
        {
            "name": "Officer Brown",
            "email": "brown@demo.fazri.com",
            "phone": "+1-555-0106",
            "role": StaffRole.SECURITY,
            "department": "Campus Security",
            "on_duty": False,  # Off duty for escalation demo
            "max_concurrent_assignments": 3,
            "contact_preferences": {"email": True, "sms": True, "push": True},
            "is_mock_user": True,
        },
        {
            "name": "Supervisor Lopez",
            "email": "lopez@demo.fazri.com",
            "phone": "+1-555-0107",
            "role": StaffRole.SUPERVISOR,
            "department": "Campus Security",
            "on_duty": True,
            "max_concurrent_assignments": 5,
            "contact_preferences": {"email": True, "sms": True, "push": True},
            "is_mock_user": True,
        },
    ]

    for staff_data in demo_staff:
        staff = StaffProfile(**staff_data)
        db.add(staff)

    db.commit()
    logger.info(f"Seeded {len(demo_staff)} demo staff accounts")


def seed_demo_staff_locations(db: Session):
    """Seed initial locations for demo staff"""

    # Get demo staff
    demo_staff = db.query(StaffProfile).filter(StaffProfile.is_mock_user == True).all()

    if not demo_staff:
        logger.warning("No demo staff found, skipping location seed")
        return

    # Check if locations already exist
    existing = db.query(StaffLocation).filter(
        StaffLocation.staff_id.in_([s.id for s in demo_staff])
    ).count()

    if existing > 0:
        logger.info(f"Demo staff locations already exist ({existing} found), skipping seed")
        return

    logger.info("Seeding demo staff locations...")

    # Define initial locations for each staff member
    location_map = {
        "Officer Johnson": {"zone_id": "LIB_ENT", "building": "Library", "floor": "1"},
        "Supervisor Rodriguez": {"zone_id": "ADMIN_LOBBY", "building": "Admin Building", "floor": "1"},
        "Officer Martinez": {"zone_id": "LAB_101", "building": "Science Building", "floor": "1"},
        "Security Chief Williams": {"zone_id": "ADMIN_LOBBY", "building": "Security HQ", "floor": "1"},
        "Dr. Kim": {"zone_id": "LAB_102", "building": "Research Building", "floor": "2"},
        "Officer Brown": {"zone_id": "GYM", "building": "Sports Complex", "floor": "1"},
        "Supervisor Lopez": {"zone_id": "CAF_01", "building": "Student Union", "floor": "1"},
    }

    for staff in demo_staff:
        loc_data = location_map.get(staff.name, {"zone_id": "ADMIN_LOBBY", "building": "Admin", "floor": "1"})
        location = StaffLocation(
            staff_id=staff.id,
            zone_id=loc_data["zone_id"],
            building=loc_data["building"],
            floor=loc_data["floor"],
            source="demo_seed",
        )
        db.add(location)

    db.commit()
    logger.info(f"Seeded locations for {len(demo_staff)} demo staff")


def init_alert_system():
    """Initialize the complete alert system database"""
    logger.info("Initializing alert system...")

    # Create tables
    create_tables()

    # Seed data
    db = SessionLocal()
    try:
        seed_demo_scenarios(db)
        seed_demo_staff(db)
        seed_demo_staff_locations(db)
        logger.info("Alert system initialization complete")
    except Exception as e:
        logger.error(f"Error during alert system initialization: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_alert_system()
