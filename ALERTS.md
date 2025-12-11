# Anomaly Alerting & Staff Assignment System - Implementation Guide

## Executive Summary

This guide outlines the implementation of a real-time alerting system that:
- Detects anomalies from your existing multi-modal campus data
- Notifies administrators immediately when anomalies occur
- Automatically assigns nearby staff members to investigate
- Allows both admins and assigned staff to mark anomalies as resolved
- Maintains audit trail of all anomaly responses
- **Includes a mock alert demonstration system for testing and demos**

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Anomaly Detection Engine                 │
│            (Existing - TensorFlow LSTM/XGBoost)             │
└─────────────────────┬───────────────────────────────────────┘
                      │ Anomaly Detected
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Alerting & Assignment Service                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Alert      │  │   Proximity  │  │  Assignment  │       │
│  │   Manager    │→ │   Resolver   │→ │   Engine     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────────────────────────────────────────┐       │
│  │        Mock Alert Generator (Demo Mode)          │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌──────────────────┐      ┌──────────────────┐
│  Admin Dashboard │      │  Staff Mobile/   │
│  (Web Interface) │      │  Web Interface   │
└──────────────────┘      └──────────────────┘
```

## Feature Specifications

### 1. Anomaly Detection Integration

**Purpose**: Bridge between existing anomaly detection and new alerting system

**Key Components**:
- **Anomaly Event Listener**: Subscribes to anomaly detection outputs
- **Severity Classification**: Categorizes anomalies (Critical/High/Medium/Low)
- **Context Enrichment**: Adds location, time, affected entities, and data sources

**Data Requirements**:
- Anomaly type (behavioral, spatial, temporal)
- Location coordinates or zone identifier
- Entity IDs involved
- Confidence score
- Source data streams (WiFi/CCTV/Card Swipe/etc.)

### 2. Alert Management System

**Purpose**: Create, track, and manage anomaly alerts through their lifecycle

**Alert States**:
```
Created → Assigned → Acknowledged → Investigating → Resolved
                                         ↓
                                    Escalated (if timeout)
```

**Alert Data Model**:
```
Alert {
  id: UUID
  anomaly_id: Reference to detection
  severity: enum(CRITICAL, HIGH, MEDIUM, LOW)
  status: enum(CREATED, ASSIGNED, ACKNOWLEDGED, INVESTIGATING, RESOLVED, ESCALATED)
  title: string
  description: string
  location: {
    zone_id: string
    coordinates: {lat, lng}
    building: string
    floor: string
  }
  affected_entities: [entity_ids]
  data_sources: [source_types]
  created_at: timestamp
  assigned_to: staff_id
  assigned_at: timestamp
  acknowledged_at: timestamp
  resolved_at: timestamp
  resolved_by: user_id
  resolution_notes: string
  escalation_count: integer
  is_mock: boolean          # NEW: Flag for demonstration alerts
  mock_scenario: string     # NEW: Scenario identifier for demos
}
```

### 3. Proximity-Based Staff Assignment

**Purpose**: Intelligently assign alerts to the most appropriate nearby staff

**Assignment Logic**:

1. **Proximity Calculation**:
   - Use most recent card swipe data to determine staff location
   - Calculate distance from anomaly location to each staff member
   - Consider staff members within configurable radius (e.g., 100m)

2. **Staff Availability**:
   - Check current workload (number of active assignments)
   - Respect max concurrent assignments per staff
   - Consider staff on-duty status
   - Factor in staff roles/permissions

3. **Assignment Priority**:
   ```
   Priority Score = (Proximity Weight × Distance) + 
                    (Workload Weight × Active Assignments) + 
                    (Skill Weight × Role Match)
   ```
   Assign to staff with lowest priority score

4. **Fallback Mechanisms**:
   - If no nearby staff: assign to on-duty supervisor
   - If no response within X minutes: escalate to admin
   - If critical severity: notify multiple staff simultaneously

**Staff Profile Requirements**:
```
Staff {
  id: UUID
  name: string
  role: enum(SECURITY, SUPERVISOR, ADMIN)
  current_location: {zone_id, last_update}
  on_duty: boolean
  max_concurrent_assignments: integer
  active_assignments: [alert_ids]
  contact_preferences: {
    email: boolean
    sms: boolean
    push: boolean
  }
  is_mock_user: boolean     # NEW: Flag for demo staff accounts
}
```

### 4. Multi-Channel Notification System

**Purpose**: Deliver alerts through multiple channels with fallback

**Notification Channels**:

1. **Admin Notifications**:
   - Real-time dashboard updates (WebSocket)
   - Email for critical alerts
   - Optional SMS for critical alerts
   - Desktop/browser push notifications

2. **Staff Notifications**:
   - Mobile push notifications (primary)
   - SMS for critical alerts
   - In-app notifications
   - Email as backup

**Notification Content**:
```
Notification {
  type: enum(ALERT_CREATED, ALERT_ASSIGNED, ALERT_ESCALATED)
  priority: enum(CRITICAL, HIGH, MEDIUM, LOW)
  title: string (e.g., "Unusual Activity Detected - Building A")
  body: string (detailed description)
  action_url: string (deep link to alert)
  data: {
    alert_id: UUID
    location: object
    severity: string
    timestamp: string
  }
  is_mock: boolean          # NEW: Suppress actual delivery for demos
}
```

**Delivery Guarantees**:
- Retry failed deliveries (max 3 attempts)
- Log all notification attempts
- Track delivery status and read receipts
- Alert admin if staff doesn't acknowledge within threshold

### 5. Staff Response Interface

**Purpose**: Enable staff to interact with assigned alerts efficiently

**Key Features**:

1. **Alert Acknowledgment**:
   - One-tap acknowledgment from notification
   - Auto-update alert status to "Acknowledged"
   - Record acknowledgment timestamp

2. **Investigation Actions**:
   - View anomaly details and evidence
   - Access related historical data
   - View real-time camera feeds (if applicable)
   - Add investigation notes
   - Request backup/assistance

3. **Resolution Workflow**:
   ```
   Resolve Alert Form:
   - Resolution type: dropdown (False Alarm, Resolved, Escalated)
   - Resolution notes: text area (required)
   - Action taken: dropdown (Investigated, Contacted Person, Security Called, etc.)
   - Attach photos/evidence: file upload (optional)
   - Estimated severity: rating (if differs from initial)
   ```

4. **Status Updates**:
   - "On my way" - updates status to Investigating
   - "At location" - adds location confirmation
   - "Resolved" - completes the workflow

### 6. Admin Dashboard Features

**Purpose**: Give admins full visibility and control over alert system

**Dashboard Components**:

1. **Real-Time Alert Feed**:
   - Live list of all active alerts
   - Color-coded by severity
   - Filter by status, severity, location, staff
   - Sort by time, priority, status
   - **Mock alert indicator badge**

2. **Alert Details Panel**:
   - Full anomaly context and data
   - Timeline of all actions
   - Assigned staff information
   - Resolution history

3. **Manual Assignment**:
   - Reassign alerts to different staff
   - Override automatic assignments
   - Assign to specific teams

4. **Alert Resolution (Admin)**:
   - Same resolution interface as staff
   - Additional option to close without staff action
   - Ability to mark as false positive

5. **Analytics Dashboard**:
   - Average response time
   - Resolution rates by staff
   - False positive rates
   - Alert trends by location/time

6. **Demo Control Panel** (NEW):
   - Toggle demo mode on/off
   - Select mock alert scenarios
   - Control alert flow progression
   - Reset demo state
   - Auto-play demo sequences

### 7. Resolution Tracking & Audit Trail

**Purpose**: Maintain complete history for compliance and analysis

**Audit Log Structure**:
```
AuditLog {
  id: UUID
  alert_id: UUID
  action: enum(CREATED, ASSIGNED, ACKNOWLEDGED, STATUS_CHANGED, 
               NOTE_ADDED, RESOLVED, ESCALATED, REASSIGNED)
  actor_id: UUID (staff or admin)
  actor_type: enum(ADMIN, STAFF, SYSTEM)
  timestamp: datetime
  details: jsonb {
    previous_state: object
    new_state: object
    reason: string
  }
  ip_address: string
  user_agent: string
  is_mock: boolean          # NEW: Flag demo audit entries
}
```

**Compliance Features**:
- Immutable audit logs
- Who resolved each alert (staff_id or admin_id)
- Timestamp precision to millisecond
- FERPA-compliant logging (no PII in logs)
- Export capability for audits

---

## 🎭 Mock Alert Demonstration System

### Purpose

Provide a complete demonstration environment that:
- Simulates realistic alert scenarios without triggering real notifications
- Allows stakeholders to experience the full alert lifecycle
- Enables testing and training without affecting production systems
- Demonstrates system capabilities for investors and customers

### Demo Mode Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Demo Control Panel                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Scenario   │  │   Timeline   │  │   Auto-Play  │       │
│  │   Selector   │  │   Controls   │  │   Engine     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Mock Alert Generator Service                     │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Pre-defined Scenarios with Scripted Progressions   │     │
│  └─────────────────────────────────────────────────────┘     │
└────────────────────────┬─────────────────────────────────────┘
                         │
         ┌───────────────┴────────────────┐
         ▼                                ▼
┌──────────────────┐            ┌──────────────────┐
│  Admin Dashboard │            │  Staff Interface │
│  (Demo View)     │            │  (Demo Account)  │
└──────────────────┘            └──────────────────┘
```

### Mock Alert Scenarios

#### Scenario 1: Unauthorized Access Attempt (Medium Severity)

**Narrative**: Multiple failed card swipe attempts at restricted lab after hours

**Timeline**:
```
T+0s   : Alert created - "Unusual Access Pattern Detected"
T+5s   : Auto-assigned to nearest security staff (Officer Johnson)
T+10s  : Officer Johnson acknowledges alert
T+15s  : Status updates to "Investigating"
T+30s  : Officer arrives at location
T+45s  : Officer resolves as "False Alarm - Authorized researcher with wrong card"
```

**Alert Details**:
```json
{
  "id": "mock-001",
  "title": "Unusual Access Pattern Detected",
  "severity": "MEDIUM",
  "location": {
    "building": "Science Building A",
    "floor": "3",
    "zone": "Lab 301",
    "coordinates": {"lat": 40.7128, "lng": -74.0060}
  },
  "description": "5 failed card swipe attempts detected at Lab 301 entrance within 2 minutes. Last successful swipe at this location was 6 hours ago.",
  "affected_entities": ["student_12345"],
  "data_sources": ["CARD_SWIPE"],
  "evidence": {
    "failed_attempts": 5,
    "time_window": "23:15 - 23:17",
    "card_holder": "Dr. Sarah Chen",
    "access_history": "Normal pattern: Mon-Fri 09:00-17:00"
  },
  "is_mock": true,
  "mock_scenario": "unauthorized_access"
}
```

#### Scenario 2: Suspicious Loitering (High Severity)

**Narrative**: Unidentified person detected in restricted area for extended period

**Timeline**:
```
T+0s   : Alert created - "Suspicious Activity - Restricted Area"
T+3s   : Auto-assigned to Security Supervisor Rodriguez
T+8s   : Supervisor Rodriguez acknowledges
T+12s  : Status updates to "Investigating"
T+20s  : Backup requested - Officer Martinez assigned
T+35s  : Both officers at location
T+50s  : Resolved as "Visitor escorted out - updated access protocols"
```

**Alert Details**:
```json
{
  "id": "mock-002",
  "title": "Suspicious Activity - Restricted Area",
  "severity": "HIGH",
  "location": {
    "building": "Engineering Complex",
    "floor": "Basement",
    "zone": "Server Room Corridor",
    "coordinates": {"lat": 40.7129, "lng": -74.0061}
  },
  "description": "Person detected in restricted server room corridor for 15+ minutes. No valid card swipes in area. Face recognition: No match in database.",
  "affected_entities": ["unknown_person_001"],
  "data_sources": ["CCTV", "CARD_SWIPE"],
  "evidence": {
    "duration": "15 minutes 32 seconds",
    "last_valid_swipe": "None in last 2 hours",
    "face_recognition": "No match",
    "movement_pattern": "Back and forth near server room door",
    "cctv_frames": ["frame_001.jpg", "frame_002.jpg", "frame_003.jpg"]
  },
  "is_mock": true,
  "mock_scenario": "suspicious_loitering"
}
```

#### Scenario 3: Multiple Simultaneous Anomalies (Critical Severity)

**Narrative**: Coordinated unusual activity across multiple locations

**Timeline**:
```
T+0s   : Alert created - "Multiple Coordinated Anomalies Detected"
T+2s   : Escalated to Security Chief immediately (Critical severity)
T+3s   : Auto-assigned to 3 security staff members simultaneously
T+7s   : All staff acknowledge
T+10s  : Security Chief views live CCTV feeds
T+25s  : Status: "All locations secured - Fire drill miscommunication"
T+40s  : Resolved with incident report
```

**Alert Details**:
```json
{
  "id": "mock-003",
  "title": "Multiple Coordinated Anomalies Detected",
  "severity": "CRITICAL",
  "location": {
    "building": "Multiple Buildings",
    "floor": "Various",
    "zone": "Campus-wide",
    "coordinates": {"lat": 40.7130, "lng": -74.0062}
  },
  "description": "Simultaneous unusual WiFi activity + abnormal movement patterns detected across 4 buildings. Pattern suggests coordinated activity. Confidence: 87%",
  "affected_entities": ["entity_001", "entity_002", "entity_003", "entity_004"],
  "data_sources": ["WIFI", "CCTV", "CARD_SWIPE"],
  "evidence": {
    "affected_buildings": ["Library", "Student Center", "Admin Building", "Engineering"],
    "unusual_wifi_devices": 15,
    "movement_correlation": "High (0.87)",
    "time_correlation": "Simultaneous within 30 seconds",
    "ai_confidence": 0.87
  },
  "is_mock": true,
  "mock_scenario": "coordinated_activity"
}
```

#### Scenario 4: After-Hours Equipment Access (Low Severity)

**Narrative**: Lab equipment usage detected outside normal hours

**Timeline**:
```
T+0s   : Alert created - "Unusual Lab Equipment Usage"
T+15s  : Auto-assigned to Lab Supervisor Dr. Kim
T+45s  : Dr. Kim acknowledges from mobile
T+60s  : Checks equipment logs remotely
T+90s  : Resolved as "Authorized - PhD student with permission"
```

**Alert Details**:
```json
{
  "id": "mock-004",
  "title": "Unusual Lab Equipment Usage",
  "severity": "LOW",
  "location": {
    "building": "Research Lab Building",
    "floor": "2",
    "zone": "Chemistry Lab 204",
    "coordinates": {"lat": 40.7131, "lng": -74.0063}
  },
  "description": "High-power centrifuge activated at 02:30 AM. Typical usage hours: 08:00-18:00. No card swipe detected within 15 minutes of activation.",
  "affected_entities": ["equipment_centrifuge_204"],
  "data_sources": ["IOT_SENSOR", "CARD_SWIPE"],
  "evidence": {
    "equipment_id": "CENT-204-A",
    "activation_time": "02:30:15",
    "last_card_swipe": "02:15:00 - Student ID 67890",
    "usage_pattern": "First after-hours use in 3 months",
    "power_consumption": "Normal range"
  },
  "is_mock": true,
  "mock_scenario": "after_hours_equipment"
}
```

#### Scenario 5: Escalation Flow Demo (High → Critical)

**Narrative**: Unacknowledged alert escalates through chain of command

**Timeline**:
```
T+0s   : Alert created - "Unattended Bag in Public Area"
T+5s   : Auto-assigned to Officer Brown
T+5m   : No acknowledgment - Auto-escalate to Supervisor
T+6m   : Supervisor Lopez acknowledges and takes over
T+7m   : Supervisor requests bomb squad assessment
T+10m  : Updated to CRITICAL severity
T+15m  : Resolved as "Student backpack - owner located and identified"
```

**Alert Details**:
```json
{
  "id": "mock-005",
  "title": "Unattended Bag in Public Area",
  "severity": "HIGH",
  "location": {
    "building": "Student Union",
    "floor": "1",
    "zone": "Main Lobby",
    "coordinates": {"lat": 40.7132, "lng": -74.0064}
  },
  "description": "Backpack left unattended in busy lobby area for 20+ minutes. No person in vicinity. Object detection confidence: 92%",
  "affected_entities": ["object_unattended_001"],
  "data_sources": ["CCTV"],
  "evidence": {
    "unattended_duration": "20 minutes 15 seconds",
    "last_person_nearby": "18 minutes ago",
    "object_type": "Backpack (92% confidence)",
    "size": "Medium (estimated 15-20L)",
    "video_clip": "union_lobby_camera3_segment.mp4"
  },
  "escalation_history": [
    {
      "from": "Officer Brown",
      "to": "Supervisor Lopez",
      "reason": "No acknowledgment after 5 minutes",
      "timestamp": "T+5m"
    }
  ],
  "is_mock": true,
  "mock_scenario": "escalation_demo"
}
```

### Demo Control Panel Features

#### 1. Scenario Selection

**UI Component**: Dropdown menu with scenario cards

```
┌─────────────────────────────────────────────────────┐
│  Select Demo Scenario                         [▼]   │
├─────────────────────────────────────────────────────┤
│  🔵 Unauthorized Access Attempt                     │
│     Medium Severity | ~45s duration                 │
│     Demonstrates: Auto-assignment, Resolution       │
├─────────────────────────────────────────────────────┤
│  🔴 Suspicious Loitering                            │
│     High Severity | ~50s duration                   │
│     Demonstrates: Backup request, Multi-staff       │
├─────────────────────────────────────────────────────┤
│  ⚠️  Multiple Coordinated Anomalies                 │
│     Critical Severity | ~40s duration               │
│     Demonstrates: Multi-assignment, Escalation      │
├─────────────────────────────────────────────────────┤
│  🟡 After-Hours Equipment Access                    │
│     Low Severity | ~90s duration                    │
│     Demonstrates: Remote resolution                 │
├─────────────────────────────────────────────────────┤
│  ⬆️  Escalation Flow Demo                           │
│     High→Critical | ~15m duration                   │
│     Demonstrates: Auto-escalation, Severity change  │
└─────────────────────────────────────────────────────┘
```

#### 2. Timeline Controls

**UI Component**: Video-style playback controls

```
┌─────────────────────────────────────────────────────┐
│  Demo Timeline                                       │
├─────────────────────────────────────────────────────┤
│  [◄◄] [▶/⏸] [►►]        ⏱️  0:15 / 0:45            │
│  ═════════════════════════════════════════          │
│  │    │         │                │                  │
│  Created  Assigned  Acknowledged  Investigating     │
│                                                      │
│  Speed: [0.5x] [1x] [2x] [5x]                      │
│  Auto-advance: [✓] After each step                 │
└─────────────────────────────────────────────────────┘
```

**Controls**:
- ◄◄ (Previous Step): Go back to previous alert state
- ▶/⏸ (Play/Pause): Auto-advance through timeline
- ►► (Next Step): Manually advance to next state
- Speed controls: Control auto-advance speed
- Auto-advance toggle: Automatically progress or manual control

#### 3. State Progression Display

**UI Component**: Step-by-step progress indicator

```
┌─────────────────────────────────────────────────────┐
│  Current State: ASSIGNED                             │
├─────────────────────────────────────────────────────┤
│  ✓ Alert Created            T+0s                    │
│  ► Alert Assigned           T+5s  ← YOU ARE HERE    │
│    Staff Acknowledged       T+10s                    │
│    Investigation Started    T+15s                    │
│    Officer At Location      T+30s                    │
│    Alert Resolved           T+45s                    │
│                                                      │
│  Next Action: Officer Johnson will acknowledge      │
│  [Skip to Next] [Auto-Play Remaining]              │
└─────────────────────────────────────────────────────┘
```

#### 4. Live Effects Display

**Shows real-time UI changes as demo progresses**:

```
┌─────────────────────────────────────────────────────┐
│  Active Demo Effects                                 │
├─────────────────────────────────────────────────────┤
│  ✓ Admin Dashboard: New alert badge appeared        │
│  ✓ Alert Feed: Mock alert added to top of list     │
│  ✓ Staff Panel: Officer Johnson shows assignment    │
│  ► Notification Panel: Toast notification sent      │
│    (Next: Officer acknowledges via mobile)          │
└─────────────────────────────────────────────────────┘
```

#### 5. Demo Reset Controls

```
┌─────────────────────────────────────────────────────┐
│  Demo Controls                                       │
├─────────────────────────────────────────────────────┤
│  [Reset Current Scenario]  - Restart from beginning │
│  [Clear All Mock Alerts]   - Remove all demo data   │
│  [Load Multiple Scenarios] - Run several in series  │
│                                                      │
│  Quick Demos:                                        │
│  [Full Walkthrough]    - All 5 scenarios (5 min)    │
│  [Critical Only]       - Scenario 3 (40 sec)        │
│  [Happy Path]          - Scenarios 1,4 (2 min)      │
└─────────────────────────────────────────────────────┘
```

#### 6. Presentation Mode

**Full-screen demo mode optimized for stakeholder presentations**:

```
┌─────────────────────────────────────────────────────┐
│  🎬 PRESENTATION MODE                                │
├─────────────────────────────────────────────────────┤
│  Features:                                           │
│  • Full-screen dashboard with minimal chrome        │
│  • Large, clear typography for projectors           │
│  • Auto-narration (text overlays explaining steps)  │
│  • Keyboard shortcuts for presenter control         │
│  • Hide technical details, show user benefits       │
│                                                      │
│  [Enter Presentation Mode]                          │
│  [Configure Presentation Settings]                  │
└─────────────────────────────────────────────────────┘
```

### Mock Staff Accounts

**Pre-configured demo staff with scripted behaviors**:

```
Demo Staff Roster:
├─ Officer Johnson (Security)
│  Location: Building A, Floor 1
│  Specialty: First responder scenarios
│  
├─ Supervisor Rodriguez (Security Supervisor)
│  Location: Security Office
│  Specialty: High-severity alerts, backup coordination
│  
├─ Officer Martinez (Security)
│  Location: Building B, Floor 2
│  Specialty: Backup support scenarios
│  
├─ Security Chief Williams (Admin)
│  Location: Security HQ
│  Specialty: Critical escalations
│  
└─ Dr. Kim (Lab Supervisor)
   Location: Research Building
   Specialty: Lab equipment alerts
```

### Mock Data Fixtures

**Pre-populated data for realistic demonstrations**:

1. **Location Data**:
   - Campus map with buildings, floors, zones
   - Staff positions at realistic locations
   - Historical movement patterns

2. **Historical Alerts**:
   - 50+ resolved mock alerts from "past week"
   - Variety of severities and outcomes
   - Complete audit trails

3. **Evidence Assets**:
   - Sample CCTV frame images
   - Mock WiFi logs
   - Sample card swipe data
   - Equipment sensor readings

4. **Analytics Data**:
   - Pre-computed metrics for dashboard
   - Charts showing alert trends
   - Staff performance statistics

### API Endpoints for Demo Control

```
POST   /api/demo/start-scenario        # Start a demo scenario
POST   /api/demo/advance-step          # Move to next step
POST   /api/demo/reset                 # Reset demo state
GET    /api/demo/scenarios             # List available scenarios
GET    /api/demo/current-state         # Get current demo state
PATCH  /api/demo/speed                 # Adjust playback speed
POST   /api/demo/auto-play             # Start auto-play mode
```

### Demo Mode Configuration

```yaml
demo_mode:
  enabled: true
  
  scenarios:
    - id: unauthorized_access
      duration: 45
      auto_advance: true
      speed: 1.0
      
    - id: suspicious_loitering
      duration: 50
      auto_advance: true
      speed: 1.0
      
    - id: coordinated_activity
      duration: 40
      auto_advance: true
      speed: 1.0
      
    - id: after_hours_equipment
      duration: 90
      auto_advance: true
      speed: 2.0
      
    - id: escalation_demo
      duration: 900  # 15 minutes
      auto_advance: false  # Manual control
      speed: 10.0  # Time compression
  
  presentation_mode:
    auto_narration: true
    font_scale: 1.5
    hide_technical_details: true
    
  notifications:
    suppress_actual_delivery: true
    show_mock_notifications: true
    notification_delay: 2  # seconds
```

### Implementation Details for Mock System

#### Database Considerations

**Mock Data Isolation**:
```sql
-- All mock alerts flagged
WHERE is_mock = true

-- Separate mock alerts from analytics
SELECT * FROM alerts 
WHERE is_mock = false  -- Production analytics

-- Demo cleanup
DELETE FROM alerts WHERE is_mock = true;
```

#### Service Layer

```python
class MockAlertService:
    def start_scenario(self, scenario_id: str):
        """Initialize mock alert scenario"""
        scenario = self.load_scenario(scenario_id)
        alert = self.create_mock_alert(scenario)
        self.schedule_timeline_events(alert, scenario.timeline)
        return alert
    
    def advance_step(self, alert_id: str):
        """Manually progress to next step"""
        alert = self.get_alert(alert_id)
        next_step = self.get_next_step(alert)
        self.execute_step(alert, next_step)
    
    def auto_play(self, alert_id: str, speed: float):
        """Automatically progress through timeline"""
        alert = self.get_alert(alert_id)
        for step in alert.remaining_steps:
            self.execute_step(alert, step)
            time.sleep(step.delay / speed)
```

#### Frontend Components

**Demo Banner**:
```
┌─────────────────────────────────────────────────────┐
│  🎭 DEMO MODE ACTIVE                                │
│  Scenario: Unauthorized Access Attempt              │
│  [View Controls] [Exit Demo]                        │
└─────────────────────────────────────────────────────┘
```

**Mock Alert Indicator**:
```
Alert Card:
┌─────────────────────────────────────────────────────┐
│  🎭 DEMO  Unusual Access Pattern Detected           │
│  MEDIUM | Building A, Lab 301                       │
│  Assigned to: Officer Johnson                       │
│  [View Details]                                     │
└─────────────────────────────────────────────────────┘
```

### Demo Walkthrough Script

**For Investor/Customer Demonstrations**:

```markdown
## 5-Minute Demo Script

### Opening (0:00 - 0:30)
"Let me show you how our system detects and responds to security 
anomalies in real-time. I'll walk through an actual scenario."

### Scenario Setup (0:30 - 1:00)
[Select "Unauthorized Access Attempt" from demo panel]
"Our AI has detected unusual card swipe patterns at a restricted 
lab after hours. Watch what happens next."

### Alert Creation (1:00 - 1:15)
[Play button - alert appears]
"The system immediately creates an alert, classifies severity, 
and shows all relevant evidence - failed swipes, location, timing."

### Auto-Assignment (1:15 - 1:30)
[Next step - assignment occurs]
"Within seconds, the system automatically assigns the nearest 
available security officer based on their location and workload."

### Staff Notification (1:30 - 1:45)
[Show staff mobile view]
"Officer Johnson receives an instant push notification on their 
mobile device with all the details they need to respond."

### Acknowledgment (1:45 - 2:00)
[Progress to acknowledgment]
"With one tap, the officer acknowledges and the admin dashboard 
updates in real-time. Everyone knows help is on the way."

### Investigation (2:00 - 3:00)
[Progress through investigation steps]
"The officer can update status, add notes, and access camera feeds 
as they investigate. All actions are logged for compliance."

### Resolution (3:00 - 3:30)
[Complete resolution]
"Once resolved, the officer documents the outcome. In this case, 
it was an authorized researcher using the wrong access card."

### Analytics (3:30 - 4:30)
[Switch to analytics dashboard]
"The system tracks all metrics - response times, resolution rates, 
and patterns. This helps optimize security operations over time."

### Q&A (4:30 - 5:00)
"Any questions? I can show you other scenarios like multi-location 
incidents or escalation flows."
```

### Testing Recommendations for Demo System

1. **Smoke Tests**:
   - All scenarios load without errors
   - Timeline progresses correctly
   - UI updates reflect state changes
   - Reset functionality works

2. **Integration Tests**:
   - WebSocket updates during demo
   - Database transactions for mock data
   - Notification system respects mock flag
   - Analytics exclude mock alerts

3. **User Acceptance Tests**:
   - Stakeholders can operate demo controls
   - Presentation mode is clear on projector
   - Auto-play timing is appropriate
   - Multiple scenarios can run in sequence

### Maintenance Considerations

**Keeping Demos Fresh**:
- Update mock scenarios quarterly
- Add new scenarios based on actual incidents (anonymized)
- Refresh sample images/data periodically
- Validate timeline durations match real system performance

**Demo Data Management**:
- Auto-purge mock alerts older than 30 days
- Maintain separate demo database (optional)
- Document all mock staff accounts
- Version control demo scenarios

---

## Technical Architecture

### Database Schema

**New Tables Required**:

1. **alerts** (main alert table)
2. **alert_assignments** (assignment history)
3. **alert_audit_log** (action history)
4. **staff_locations** (real-time location tracking)
5. **notification_queue** (pending notifications)
6. **notification_log** (delivery tracking)
7. **demo_scenarios** (mock scenario definitions) ← NEW
8. **demo_timeline_events** (scenario step definitions) ← NEW

**Modifications to Existing Tables**:
- **staff_profiles**: Add fields for on_duty, max_assignments, notification preferences, is_mock_user
- **anomaly_detections**: Add alert_id foreign key
- **alerts**: Add is_mock, mock_scenario fields

### API Endpoints

**Alert Management**:
```
POST   /api/alerts                    # Create alert (system)
GET    /api/alerts                    # List alerts (filtered)
GET    /api/alerts/:id                # Get alert details
PATCH  /api/alerts/:id/status         # Update alert status
POST   /api/alerts/:id/assign         # Assign to staff
POST   /api/alerts/:id/acknowledge    # Staff acknowledges
POST   /api/alerts/:id/resolve        # Resolve alert
GET    /api/alerts/:id/audit-log      # Get alert history
```

**Demo Control** (NEW):
```
POST   /api/demo/start-scenario       # Start demo scenario
POST   /api/demo/advance-step         # Progress to next step
POST   /api/demo/reset                # Reset demo state
GET    /api/demo/scenarios            # List scenarios
GET    /api/demo/current-state        # Get current state
PATCH  /api/demo/speed                # Adjust speed
POST   /api/demo/auto-play            # Start auto-play
DELETE /api/demo/alerts               # Clear mock alerts
```

**Staff Management**:
```
GET    /api/staff/nearby              # Get staff near location
GET    /api/staff/:id/assignments     # Get staff's active alerts
PATCH  /api/staff/:id/location        # Update staff location
PATCH  /api/staff/:id/availability    # Update on-duty status
```

**Notification Endpoints**:
```
POST   /api/notifications/send        # Send notification (internal)
GET    /api/notifications/history     # Get notification log
POST   /api/notifications/test        # Test notification setup
```

**WebSocket Events**:
```
// Server → Client
alert.created
alert.assigned
alert.updated
alert.resolved
staff.location_updated
demo.step_advanced          ← NEW
demo.scenario_started       ← NEW
demo.scenario_completed     ← NEW

// Client → Server
alert.acknowledge
alert.status_change
location.update
demo.control                ← NEW
```

### Service Architecture

**Microservices Approach** (Recommended):

1. **Alert Service**:
   - Manages alert lifecycle
   - Assignment logic
   - Status transitions

2. **Notification Service**:
   - Multi-channel delivery
   - Queue management
   - Retry logic

3. **Location Service**:
   - Staff location tracking
   - Proximity calculations
   - Zone management

4. **Audit Service**:
   - Log all actions
   - Compliance reporting
   - Analytics

5. **Demo Service** (NEW):
   - Scenario management
   - Timeline orchestration
   - Mock data generation
   - Auto-play control

**Communication**:
- REST APIs for synchronous operations
- Message Queue (e.g., RabbitMQ, AWS SQS) for async notifications
- WebSocket for real-time updates
- Event bus for demo state changes

### Technology Stack Recommendations

**Backend**:
- FastAPI for new services (matches your existing stack)
- PostgreSQL for alert/staff data
- Redis for real-time location caching
- WebSocket (Socket.io or FastAPI WebSocket)

**Notification Services**:
- **Push Notifications**: Firebase Cloud Messaging (FCM) or AWS SNS
- **Email**: SendGrid or AWS SES
- **SMS**: Twilio or AWS SNS

**Frontend**:
- Real-time dashboard: Next.js + WebSocket
- Staff mobile: React Native or PWA
- UI components: ShadCN (your existing choice)
- Demo controls: Custom React components

**Demo Assets**:
- Sample images: S3 or static CDN
- Mock data: JSON fixtures
- Video clips: Compressed MP4 files

### Security & Privacy

**Authentication & Authorization**:
- JWT tokens for API access
- Role-based access control (RBAC)
- Staff can only view/resolve their assigned alerts
- Admins have full access
- Demo mode requires admin role

**Data Protection**:
- Encrypt sensitive data at rest
- TLS for all communications
- Audit logging of all access
- FERPA compliance for student data
- Staff location data retention policy (e.g., 30 days)
- Mock data clearly flagged (cannot be confused with real data)

**Rate Limiting**:
- Prevent notification spam
- Throttle API requests
- Escalation cooldown periods
- Demo API separate rate limits

## Implementation Phases

### Phase 1: Core Alert System (Weeks 1-2)
**Goal**: Basic alert creation and tracking

**Deliverables**:
- Database schema implementation
- Alert creation from anomaly detection
- Basic admin dashboard
- Alert status management

**Epics**:
1. Alert Data Model & Database Setup
2. Alert Creation Service
3. Basic Admin Dashboard UI
4. Alert Status Management

### Phase 2: Staff Assignment (Weeks 3-4)
**Goal**: Automated staff assignment based on proximity

**Deliverables**:
- Staff location tracking
- Proximity calculation service
- Assignment algorithm
- Staff profile management

**Epics**:
1. Staff Location Tracking System
2. Proximity-Based Assignment Engine
3. Staff Profile Management UI
4. Assignment Algorithm Implementation

### Phase 3: Notification System (Weeks 5-6)
**Goal**: Multi-channel notification delivery

**Deliverables**:
- Notification service
- Admin email/dashboard notifications
- Staff push notifications
- SMS for critical alerts

**Epics**:
1. Notification Service Architecture
2. Admin Notification Channels
3. Staff Push Notification System
4. SMS Integration for Critical Alerts

### Phase 4: Staff Interface (Weeks 7-8)
**Goal**: Staff response and resolution tools

**Deliverables**:
- Staff mobile/web interface
- Acknowledgment workflow
- Resolution workflow
- Investigation tools

**Epics**:
1. Staff Mobile/Web Interface
2. Alert Acknowledgment Feature
3. Resolution Workflow
4. Investigation Tools Integration

### Phase 5: Mock Alert Demonstration System (Weeks 9-10)
**Goal**: Complete demo system for stakeholder presentations

**Deliverables**:
- Demo control panel
- 5 pre-defined scenarios
- Auto-play functionality
- Presentation mode
- Mock data fixtures

**Epics**:
1. Demo Service Architecture & API
2. Demo Control Panel UI
3. Mock Alert Scenarios Implementation
4. Auto-Play Timeline Engine
5. Presentation Mode & Demo Assets

### Phase 6: Advanced Features (Weeks 11-12)
**Goal**: Escalation, analytics, and optimization

**Deliverables**:
- Escalation logic
- Analytics dashboard
- Audit trail reporting
- Performance optimization

**Epics**:
1. Alert Escalation System
2. Analytics Dashboard
3. Audit Trail & Compliance Reporting
4. System Performance Optimization

## Integration Points

### With Existing Anomaly Detection

**Required Changes**:
1. Anomaly detection outputs must publish events to alert system
2. Event payload must include:
   - Anomaly type and severity
   - Location information
   - Entity IDs
   - Confidence score
   - Data sources used

**Integration Pattern**:
```
Anomaly Detection → Event Bus → Alert Service → Assignment Engine
                        ↓
                  Demo Service (if demo mode active)
```

### With Campus Card Swipe System

**Required Access**:
- Real-time staff location from card swipes
- Historical location data for proximity
- Staff profile information

**Data Flow**:
```
Card Swipe Event → Location Service → Cache (Redis) → Assignment Engine
                                          ↓
                                    Demo Service (mock locations)
```

### With Admin Dashboard

**New Components**:
- Alert feed widget
- Alert detail modal
- Staff location map
- Alert analytics charts
- Demo control panel (NEW)
- Demo mode toggle (NEW)

**Real-time Updates**:
- WebSocket connection for live alerts
- Auto-refresh on status changes
- Desktop notifications
- Demo state synchronization (NEW)

## Configuration & Tunables

### Assignment Parameters
```yaml
proximity:
  max_distance_meters: 100
  search_radius_growth: 50  # grow by 50m if no staff found
  max_search_radius: 500

assignment:
  max_concurrent_per_staff: 3
  prefer_lighter_workload: true
  
  weights:
    proximity: 0.5
    workload: 0.3
    skill_match: 0.2

escalation:
  no_acknowledgment_minutes: 5
  no_resolution_minutes: 30
  max_escalations: 2
```

### Notification Settings
```yaml
notifications:
  admin:
    channels: [dashboard, email]
    critical_sms: true
    
  staff:
    channels: [push, sms]
    push_priority: high
    
  retry:
    max_attempts: 3
    backoff_seconds: [10, 60, 300]
    
  demo_mode:                  # NEW
    suppress_delivery: true
    show_mock_ui: true
```

### Alert Severity Thresholds
```yaml
severity_mapping:
  critical:
    confidence_min: 0.9
    immediate_notify: true
    multi_staff_assign: true
    
  high:
    confidence_min: 0.7
    immediate_notify: true
    
  medium:
    confidence_min: 0.5
    
  low:
    confidence_min: 0.3
```

### Demo Configuration (NEW)
```yaml
demo_mode:
  enabled: true
  default_speed: 1.0
  auto_advance: true
  
  scenarios:
    - unauthorized_access
    - suspicious_loitering
    - coordinated_activity
    - after_hours_equipment
    - escalation_demo
    
  presentation:
    auto_narration: true
    font_scale: 1.5
```

## Testing Strategy

### Unit Tests
- Assignment algorithm logic
- Proximity calculations
- Notification delivery
- Status transitions
- Demo timeline progression (NEW)
- Mock data generation (NEW)

### Integration Tests
- End-to-end alert workflow
- Multi-service communication
- Notification delivery
- Database operations
- Demo scenario execution (NEW)
- WebSocket demo events (NEW)

### Load Testing
- Concurrent alert handling
- Notification queue processing
- WebSocket connections
- Staff location updates

### User Acceptance Testing
- Admin creates and resolves alert manually
- Staff receives and acknowledges alert
- Staff resolves alert from mobile
- Escalation flow triggered
- Analytics dashboard accuracy
- **Demo mode: All scenarios complete successfully** (NEW)
- **Demo mode: Auto-play functions correctly** (NEW)
- **Demo mode: Presentation mode is clear on projector** (NEW)

### Demo-Specific Testing (NEW)
- All 5 scenarios load and complete
- Timeline controls work correctly
- Reset functionality clears state
- Mock data doesn't pollute analytics
- Presentation mode displays properly
- Auto-narration text is accurate

## Monitoring & Operations

### Key Metrics
- Alert creation rate
- Average assignment time
- Average acknowledgment time
- Average resolution time
- False positive rate
- Staff response rate
- Notification delivery success rate
- **Demo mode usage frequency** (NEW)
- **Demo scenario completion rate** (NEW)

### Alerts & Thresholds
- High unassigned alert count (> 5)
- Slow assignment time (> 30s)
- Notification delivery failures (> 5%)
- Unacknowledged critical alerts (> 2 min)
- High escalation rate (> 20%)

### Logging
- All alert state changes
- All assignment decisions
- All notification attempts
- All staff actions
- System errors and warnings
- **All demo mode activations** (NEW)
- **Demo scenario executions** (NEW)

## Success Criteria

### Functional
- ✅ Alerts created automatically from anomalies
- ✅ Staff assigned within 30 seconds
- ✅ Admins receive real-time notifications
- ✅ Staff can acknowledge from mobile
- ✅ Alerts can be resolved by staff or admin
- ✅ Complete audit trail maintained
- ✅ **Demo mode: All 5 scenarios demonstrate successfully** (NEW)
- ✅ **Demo mode: Stakeholders can operate controls** (NEW)
- ✅ **Demo mode: Presentation mode impresses investors** (NEW)

### Performance
- ✅ Assignment time < 30 seconds (p95)
- ✅ Notification delivery < 5 seconds (p95)
- ✅ Dashboard loads < 2 seconds
- ✅ Support 100+ concurrent active alerts
- ✅ WebSocket latency < 200ms
- ✅ **Demo scenarios complete within expected timeframes** (NEW)

### Reliability
- ✅ 99.9% uptime for alert service
- ✅ Zero data loss in alert creation
- ✅ 95%+ notification delivery success
- ✅ Graceful degradation if services down
- ✅ **Demo mode: Never crashes during presentation** (NEW)

## Next Steps

1. **Review & Refinement**:
   - Validate with stakeholders
   - Refine requirements based on feedback
   - Prioritize features for MVP
   - **Review mock scenarios with marketing team** (NEW)

2. **Technical Design**:
   - Create detailed technical architecture document
   - Define database schema
   - Design API contracts
   - Plan deployment strategy
   - **Design demo service architecture** (NEW)

3. **Development Setup**:
   - Set up development environment
   - Configure notification service accounts
   - Create test data sets
   - Establish coding standards
   - **Prepare demo asset library** (NEW)

4. **Begin Phase 1**:
   - Start with Core Alert System
   - Implement iteratively
   - Test continuously
   - **Plan demo system development in Phase 5** (NEW)

---

## Additional Considerations

### Scalability
- Design for horizontal scaling
- Use message queues for async processing
- Cache frequently accessed data (staff locations)
- Database indexing for alert queries

### Future Enhancements
- Machine learning for false positive reduction
- Predictive staffing based on patterns
- Integration with incident management systems
- Mobile app for staff with offline support
- Video clip capture on alert creation
- Geofencing for automatic location updates
- Voice-activated alert acknowledgment
- **Interactive 3D campus visualization for demos** (NEW)
- **VR walkthrough of alert response** (NEW)
- **AI-powered demo customization based on audience** (NEW)

### Training & Documentation
- Admin user guide
- Staff mobile app guide
- API documentation
- Incident response procedures
- On-call handbook
- **Demo operation guide for sales team** (NEW)
- **Presentation scripts for different audiences** (NEW)

### Demo System Benefits

**For Sales & Marketing**:
- Demonstrate full system without production access
- Customize scenarios for specific customer concerns
- Show system capabilities in controlled environment
- Collect feedback without risk to production

**For Training**:
- Train new security staff on procedures
- Practice incident response without real incidents
- Test staff readiness with simulated alerts
- Onboard new team members safely

**For Development**:
- Test new features end-to-end
- Verify UI/UX changes in realistic scenarios
- Debug complex workflows
- Regression testing with known scenarios

**For Stakeholders**:
- Board presentations with live demonstrations
- Investor showcases
- Customer pilots and trials
- Regulatory compliance demonstrations

---

This comprehensive guide now includes a complete mock alert demonstration system that will enable you to:

1. **Demonstrate system capabilities** to investors and customers
2. **Train staff** on incident response procedures
3. **Test and validate** new features safely
4. **Present live** in board meetings and sales presentations
5. **Collect feedback** without impacting production systems

The mock system is designed to be indistinguishable from real alerts during presentations while being completely isolated from production operations. All demo data is clearly flagged and can be easily cleared, ensuring no confusion between demo and real incidents.
