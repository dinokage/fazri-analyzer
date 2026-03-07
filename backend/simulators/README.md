# Data Source Simulators

This directory contains Docker-based simulators for testing the Fazri Analyzer data pipeline without access to real hardware.

## Overview

The simulators provide realistic data that mimics actual campus systems:

- **eSSL Card Reader Simulator** - MySQL database with 90 days of card swipe events
- **Omada WiFi Simulator** (Coming soon) - REST API mock server with WiFi connection logs
- **CCTV Simulator** (Coming soon) - Image-based face detection events

## eSSL Card Reader Simulator

### Features

- **Realistic MySQL database** matching eSSL X990/K90 series schema
- **90 days of historical data** with temporal patterns
- **400 simulated users:**
  - 300 Students
  - 50 Faculty
  - 30 Staff
  - 20 Visitors
- **10 entry points/doors** across campus
- **Realistic behavior patterns:**
  - Morning arrival rush (8-10 AM)
  - Lunch time movement (12-1 PM)
  - Evening departure (4-8 PM)
  - Weekend patterns (reduced activity)
  - Late night access (researchers, security)
- **Anomalies included for testing:**
  - Unusual late-night access
  - Rapid multiple swipes (tailgating)
  - Weekend access by weekday-only users

### Quick Start

1. **Start the MySQL database:**
   ```bash
   cd backend/simulators
   docker-compose -f docker-compose.simulators.yml up -d essl-mysql
   ```

2. **Wait for MySQL to be ready** (about 30 seconds):
   ```bash
   docker-compose -f docker-compose.simulators.yml ps
   # Wait until essl-mysql shows "healthy"
   ```

3. **Generate the 90 days of data:**
   ```bash
   docker-compose -f docker-compose.simulators.yml run --rm essl-data-generator
   ```

   This will:
   - Create 400 user profiles
   - Generate ~50,000-70,000 card swipe events over 90 days
   - Add anomalous events for testing
   - Takes about 1-2 minutes

4. **Verify the data:**
   ```bash
   docker exec -it essl-simulator-mysql mysql -u root -pessl_password essl_db -e "
   SELECT COUNT(*) as total_events FROM AccessLogs;
   SELECT DATE(AccessTime) as date, COUNT(*) as events
   FROM AccessLogs
   GROUP BY DATE(AccessTime)
   ORDER BY date DESC
   LIMIT 7;"
   ```

### Database Connection Details

**For local testing:**
```
Host: localhost
Port: 3307
User: root
Password: essl_password
Database: essl_db
Table: AccessLogs
```

**For Docker containers:**
```
Host: essl-mysql
Port: 3306
User: root
Password: essl_password
Database: essl_db
Table: AccessLogs
```

### Testing the Connector

Test that your eSSL connector can read the simulated data:

```bash
cd backend/simulators/essl_simulator
python test_connector.py
```

This will:
- Test database connection
- Fetch sample data
- Normalize fields
- Query recent events
- Verify data quality

### Database Schema

**AccessLogs Table:**
```sql
LogID       INT AUTO_INCREMENT PRIMARY KEY
UserID      VARCHAR(50)   -- E.g., S0001, F0001, T0001
CardNo      VARCHAR(50)   -- E.g., CARD000001
AccessTime  DATETIME      -- Event timestamp
DoorID      VARCHAR(50)   -- E.g., MAIN_ENTRANCE, LIBRARY_ENTRY
EventType   VARCHAR(50)   -- IN or OUT
VerifyMode  VARCHAR(50)   -- CARD (default)
```

**Users Table:**
```sql
UserID      VARCHAR(50) PRIMARY KEY
Name        VARCHAR(100)
CardNo      VARCHAR(50) UNIQUE
Department  VARCHAR(100)
Role        VARCHAR(50)  -- Student, Faculty, Staff, Visitor
Active      BOOLEAN
```

**Doors Table:**
```sql
DoorID      VARCHAR(50) PRIMARY KEY
DoorName    VARCHAR(100)
Location    VARCHAR(100)
BuildingName VARCHAR(100)
```

### Sample Queries

**Get recent events:**
```sql
SELECT UserID, CardNo, AccessTime, DoorID, EventType
FROM AccessLogs
WHERE AccessTime >= DATE_SUB(NOW(), INTERVAL 1 DAY)
ORDER BY AccessTime DESC
LIMIT 10;
```

**Get events by user:**
```sql
SELECT u.Name, u.Role, a.AccessTime, a.DoorID, a.EventType
FROM AccessLogs a
JOIN Users u ON a.UserID = u.UserID
WHERE u.UserID = 'S0001'
ORDER BY a.AccessTime DESC
LIMIT 20;
```

**Get door usage statistics:**
```sql
SELECT DoorID, EventType, COUNT(*) as count
FROM AccessLogs
GROUP BY DoorID, EventType
ORDER BY count DESC;
```

**Find late-night access (potential anomalies):**
```sql
SELECT u.Name, u.Role, a.AccessTime, a.DoorID
FROM AccessLogs a
JOIN Users u ON a.UserID = u.UserID
WHERE HOUR(a.AccessTime) BETWEEN 0 AND 5
ORDER BY a.AccessTime DESC
LIMIT 20;
```

### Configuration for Data Pipeline

To use this simulator with the data pipeline, set these environment variables:

```bash
# Enable eSSL connector
ESSL_ENABLED=true

# Database connection (local testing)
ESSL_DB_HOST=localhost
ESSL_DB_PORT=3307
ESSL_DB_USER=root
ESSL_DB_PASSWORD=essl_password
ESSL_DB_NAME=essl_db
ESSL_TABLE_NAME=AccessLogs

# Polling interval (5 minutes)
ESSL_POLL_INTERVAL=300
```

### Data Statistics

After generation, you'll have approximately:

- **Total Users:** 400
- **Total Events:** 50,000 - 70,000
- **Date Range:** Last 90 days
- **Average Events/Day:** 600 - 800
- **Peak Hours:** 8-10 AM, 12-1 PM, 5-6 PM
- **Anomalies:** ~50-100 events for testing

### Regenerating Data

To regenerate fresh data:

```bash
# Stop and remove the database
docker-compose -f docker-compose.simulators.yml down -v

# Start fresh
docker-compose -f docker-compose.simulators.yml up -d essl-mysql

# Wait for MySQL to be ready, then regenerate
docker-compose -f docker-compose.simulators.yml run --rm essl-data-generator
```

### Troubleshooting

**MySQL container not starting:**
```bash
# Check logs
docker logs essl-simulator-mysql

# Check if port 3307 is in use
lsof -i :3307
```

**Connection refused:**
```bash
# Verify MySQL is running and healthy
docker-compose -f docker-compose.simulators.yml ps

# Check network connectivity
docker exec essl-simulator-mysql mysqladmin ping -h localhost -u root -pessl_password
```

**Data generation fails:**
```bash
# Check if MySQL is ready
docker-compose -f docker-compose.simulators.yml logs essl-mysql

# Verify database exists
docker exec -it essl-simulator-mysql mysql -u root -pessl_password -e "SHOW DATABASES;"
```

**Empty results from connector:**
```bash
# Verify data exists
docker exec -it essl-simulator-mysql mysql -u root -pessl_password essl_db -e "SELECT COUNT(*) FROM AccessLogs;"

# Check date range
docker exec -it essl-simulator-mysql mysql -u root -pessl_password essl_db -e "SELECT MIN(AccessTime), MAX(AccessTime) FROM AccessLogs;"
```

## Future Simulators

### Omada WiFi Simulator (Planned)
- REST API mock server
- OAuth 2.0 authentication
- WiFi connection/disconnection events
- MAC address hashing
- Roaming patterns

### CCTV Simulator (Planned)
- Mock RTSP stream or image directory
- Face detection events
- Multiple camera zones
- Synthetic face images for testing

## Docker Compose Commands

```bash
# Start all simulators
docker-compose -f docker-compose.simulators.yml up -d

# Start specific simulator
docker-compose -f docker-compose.simulators.yml up -d essl-mysql

# View logs
docker-compose -f docker-compose.simulators.yml logs -f essl-mysql

# Stop all simulators
docker-compose -f docker-compose.simulators.yml down

# Stop and remove data volumes (fresh start)
docker-compose -f docker-compose.simulators.yml down -v

# Check status
docker-compose -f docker-compose.simulators.yml ps
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│          eSSL Card Reader Simulator                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐    ┌─────────────────────────┐  │
│  │ MySQL 8.0    │    │ Data Generator          │  │
│  │ Database     │◄───│ (Python Script)         │  │
│  │              │    │ - 400 users             │  │
│  │ - AccessLogs │    │ - 90 days history       │  │
│  │ - Users      │    │ - Realistic patterns    │  │
│  │ - Doors      │    │ - Anomalies             │  │
│  └──────┬───────┘    └─────────────────────────┘  │
│         │                                          │
│         │ Port 3307                                │
└─────────┼──────────────────────────────────────────┘
          │
          ▼
  ┌───────────────────┐
  │ eSSL Connector    │
  │ (Your Pipeline)   │
  └───────────────────┘
```

## Contributing

To add a new simulator:

1. Create a directory: `simulators/<name>_simulator/`
2. Add init scripts and data generators
3. Update `docker-compose.simulators.yml`
4. Create test script
5. Update this README

---

**Generated:** 2026-03-07
**Author:** Claude Code (Anthropic Sonnet 4.5)
