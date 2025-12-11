# Alert System Guide

This guide explains the Alert System architecture and how to use the interactive demo flow.

## Table of Contents
- [System Overview](#system-overview)
- [Core Components](#core-components)
- [API Endpoints](#api-endpoints)
- [Demo System](#demo-system)
- [Alert Lifecycle](#alert-lifecycle)
- [Configuration](#configuration)

---

## System Overview

The Alert System is a comprehensive security alert management platform designed for campus security monitoring. It provides:

- **Real-time alert creation** from anomaly detection
- **Intelligent staff assignment** based on availability, skills, and proximity
- **Multi-channel notifications** (email, SMS, push)
- **Staff workflow management** (acknowledge, investigate, resolve)
- **Automatic escalation** for unacknowledged alerts
- **Full audit trail** of all actions
- **Interactive demo scenarios** for training and presentations

---

## Core Components

### 1. Alert Service (`services/alerts/alert_service.py`)
Handles CRUD operations for alerts:
- Create alerts from anomaly detection
- Update alert status and details
- Assign/reassign alerts to staff
- Acknowledge and resolve alerts
- Add investigation notes

### 2. Staff Service (`services/alerts/staff_service.py`)
Manages security staff:
- Staff profiles with roles and skills
- Availability tracking (on-duty, off-duty, busy)
- Workload management
- Shift scheduling

### 3. Assignment Engine (`services/alerts/assignment_engine.py`)
Intelligent alert routing:
- Scores staff based on availability, workload, skills, and proximity
- Handles critical alerts with multi-staff assignment
- Automatic fallback when primary assignee unavailable

### 4. Notification Service (`services/alerts/notification_service.py`)
Multi-channel notifications:
- Email (SMTP)
- SMS (Twilio)
- Push notifications (Firebase)
- Queue-based processing with retry logic

### 5. Demo Service (`services/alerts/demo_service.py`)
Interactive demonstrations:
- Predefined scenarios with timeline events
- Auto-advance with speed control
- Pause/resume functionality
- Real-time state tracking

---

## API Endpoints

### Alerts (`/api/v1/alerts`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all alerts (with filtering) |
| POST | `/` | Create a new alert |
| GET | `/{alert_id}` | Get alert details |
| PATCH | `/{alert_id}` | Update alert |
| POST | `/{alert_id}/assign` | Assign to staff |
| POST | `/{alert_id}/acknowledge` | Acknowledge alert |
| POST | `/{alert_id}/resolve` | Resolve alert |
| POST | `/{alert_id}/escalate` | Escalate alert |
| GET | `/{alert_id}/history` | Get audit history |

### Staff (`/api/v1/staff`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all staff |
| GET | `/{staff_id}` | Get staff details |
| GET | `/{staff_id}/dashboard` | Staff dashboard with stats |
| GET | `/{staff_id}/alerts` | Get assigned alerts |
| POST | `/{staff_id}/alerts/{alert_id}/start-investigation` | Start investigating |
| POST | `/{staff_id}/alerts/{alert_id}/add-note` | Add investigation note |
| POST | `/{staff_id}/alerts/{alert_id}/request-backup` | Request backup |
| POST | `/{staff_id}/go-off-duty` | Go off duty (reassigns alerts) |

### Notifications (`/api/v1/notifications`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/queue` | View notification queue |
| POST | `/process` | Process pending notifications |
| GET | `/history/{staff_id}` | Staff notification history |

### Demo (`/api/v1/demo`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/scenarios` | List available scenarios |
| GET | `/scenarios/{id}` | Get scenario details |
| GET | `/state` | Get current demo state |
| POST | `/start/{scenario_id}` | Start a scenario |
| POST | `/stop` | Stop current demo |
| POST | `/pause` | Pause demo |
| POST | `/resume` | Resume demo |
| POST | `/advance` | Manually advance step |
| POST | `/speed?speed=X` | Set playback speed |
| POST | `/quick-start?preset=X` | Quick start with preset |

---

## Demo System

### Available Scenarios

| Scenario ID | Description | Severity | Duration |
|-------------|-------------|----------|----------|
| `unauthorized_access` | Failed card swipe attempts at restricted area | Medium | 45s |
| `suspicious_loitering` | Person loitering near sensitive area | Medium | 50s |
| `coordinated_activity` | Multiple suspicious actors in coordination | Critical | 60s |
| `after_hours_equipment` | Equipment accessed outside normal hours | Low | 40s |
| `escalation_demo` | Full escalation chain demonstration | High | 120s |

### Quick Start (Recommended)

Start a demo with optimized settings:

```bash
# Unauthorized access demo at 3x speed
curl -X POST "http://localhost:8000/api/v1/demo/quick-start?preset=unauthorized_access"

# Critical coordinated activity at 2x speed
curl -X POST "http://localhost:8000/api/v1/demo/quick-start?preset=coordinated_activity"

# Escalation demo at 30x speed (for quick overview)
curl -X POST "http://localhost:8000/api/v1/demo/quick-start?preset=escalation_demo"
```

### Manual Control

```bash
# Start with custom settings
curl -X POST "http://localhost:8000/api/v1/demo/start/unauthorized_access?speed=5&auto_advance=true"

# Check current state
curl "http://localhost:8000/api/v1/demo/state"

# Pause the demo
curl -X POST "http://localhost:8000/api/v1/demo/pause"

# Resume the demo
curl -X POST "http://localhost:8000/api/v1/demo/resume"

# Manually advance to next step
curl -X POST "http://localhost:8000/api/v1/demo/advance"

# Change playback speed
curl -X POST "http://localhost:8000/api/v1/demo/speed?speed=10"

# Stop and cleanup
curl -X POST "http://localhost:8000/api/v1/demo/stop"
```

### Demo State Response

```json
{
  "scenario_id": "unauthorized_access",
  "scenario_name": "Unauthorized Access Attempt",
  "alert_id": "e77b0b5e-b036-4e7a-964c-7e71175a02b6",
  "current_step": 3,
  "total_steps": 6,
  "current_status": "acknowledge",
  "elapsed_seconds": 15.5,
  "speed": 3.0,
  "paused": false,
  "auto_advance": true,
  "next_step_description": "Officer starts investigation",
  "next_step_in_seconds": 2.5
}
```

### Timeline Events

Each scenario has a timeline of events that execute automatically:

1. **create** - Alert is created from anomaly detection
2. **assign** - Alert assigned to available staff
3. **acknowledge** - Staff acknowledges the alert
4. **status_change** - Status updated to "investigating"
5. **note_add** - Investigation notes added
6. **resolve** - Alert resolved with outcome

---

## Alert Lifecycle

```
┌─────────────┐
│   CREATED   │  Alert generated from anomaly
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  ASSIGNED   │  Staff member assigned
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ ACKNOWLEDGED│  Staff confirms receipt
└──────┬──────┘
       │
       ▼
┌─────────────┐
│INVESTIGATING│  Active investigation
└──────┬──────┘
       │
       ├──────────────┐
       ▼              ▼
┌─────────────┐ ┌─────────────┐
│  RESOLVED   │ │  ESCALATED  │
└─────────────┘ └─────────────┘
```

### Alert Severities

| Severity | Response Time | Staff Assignment |
|----------|---------------|------------------|
| Critical | Immediate | Multiple staff notified |
| High | < 5 minutes | Primary + backup |
| Medium | < 15 minutes | Single staff |
| Low | < 30 minutes | Single staff |

### Resolution Types

- `resolved` - Issue addressed successfully
- `false_alarm` - No actual security threat
- `escalated` - Escalated to higher authority
- `no_action_required` - Informational only

---

## Configuration

### Environment Variables

```env
# Alert System
ALERT_SYSTEM_ENABLED=true

# Notifications
EMAIL_ENABLED=true
SMS_ENABLED=true
PUSH_ENABLED=true
NOTIFICATION_MOCK_MODE=true  # Set to false in production

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=alerts@yourdomain.com

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM_NUMBER=+1234567890

# Push (Firebase)
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json
```

### Database Tables

The alert system uses these tables:

- `alerts` - Alert records
- `staff_profiles` - Security staff
- `staff_schedules` - Shift schedules
- `alert_assignments` - Assignment history
- `alert_notes` - Investigation notes
- `audit_log` - Full audit trail
- `notification_queue` - Pending notifications
- `notification_log` - Sent notifications
- `demo_scenarios` - Demo configurations
- `demo_timeline_events` - Demo timeline steps

---

## Example: Complete Alert Flow

```bash
# 1. Create an alert
curl -X POST "http://localhost:8000/api/v1/alerts" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Suspicious Activity Detected",
    "description": "Unknown individual observed near server room",
    "severity": "high",
    "location": {"zone_id": "SERVER_ROOM", "building": "IT Building"},
    "anomaly_type": "suspicious_behavior"
  }'

# 2. Assign to staff (or let auto-assignment handle it)
curl -X POST "http://localhost:8000/api/v1/alerts/{alert_id}/assign" \
  -H "Content-Type: application/json" \
  -d '{"staff_id": "7011b698-034c-4e90-952b-4f3ebd66231c"}'

# 3. Staff acknowledges
curl -X POST "http://localhost:8000/api/v1/alerts/{alert_id}/acknowledge" \
  -H "Content-Type: application/json" \
  -d '{"staff_id": "7011b698-034c-4e90-952b-4f3ebd66231c"}'

# 4. Start investigation
curl -X POST "http://localhost:8000/api/v1/staff/{staff_id}/alerts/{alert_id}/start-investigation"

# 5. Add investigation notes
curl -X POST "http://localhost:8000/api/v1/staff/{staff_id}/alerts/{alert_id}/add-note" \
  -H "Content-Type: application/json" \
  -d '{"note": "Arrived at location. Individual identified as contractor."}'

# 6. Resolve the alert
curl -X POST "http://localhost:8000/api/v1/alerts/{alert_id}/resolve" \
  -H "Content-Type: application/json" \
  -d '{
    "staff_id": "7011b698-034c-4e90-952b-4f3ebd66231c",
    "resolution_type": "false_alarm",
    "resolution_notes": "Verified contractor with valid badge"
  }'
```

---

## Troubleshooting

### Demo not advancing
- Check if `auto_advance` is enabled
- Verify speed is > 0
- Check server logs for errors

### Notifications not sending
- Verify `NOTIFICATION_MOCK_MODE=false` for production
- Check provider credentials (SMTP, Twilio, Firebase)
- Review notification queue: `GET /api/v1/notifications/queue`

### Staff assignment failing
- Ensure staff are on-duty and available
- Check staff workload limits
- Verify staff skills match alert type

### Database errors
- Run migrations: `python -m database.init_alerts`
- Check database connectivity
- Verify all tables are created

---

## Support

For issues or feature requests, please refer to the main project documentation or create an issue in the repository.
