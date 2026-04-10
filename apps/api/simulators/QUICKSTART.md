# eSSL Simulator Quick Start Guide

## Setup on Server (Where Docker is Running)

### Step 1: Start the MySQL Simulator

```bash
cd /path/to/fazri-analyzer/backend/simulators
docker-compose -f docker-compose.simulators.yml up -d essl-mysql
```

**Wait about 30 seconds** for MySQL to initialize. Check status:

```bash
docker-compose -f docker-compose.simulators.yml ps
```

You should see `essl-mysql` with status "healthy".

### Step 2: Generate 90 Days of Data

```bash
docker-compose -f docker-compose.simulators.yml run --rm essl-data-generator
```

This will:
- Install dependencies
- Generate 400 user profiles
- Create ~50,000-70,000 card swipe events
- Add anomalous patterns
- Takes 1-2 minutes

**Expected output:**
```
============================================================
eSSL Card Reader Data Generator
============================================================

Connecting to MySQL at essl-mysql:3306...
✓ Connected to database

Generating user profiles...
✓ Generated 400 user profiles:
  - Students: 300
  - Faculty: 50
  - Staff: 30
  - Visitors: 20

Inserting 400 users...
✓ 400 users inserted

Generating 90 days of card swipe events...
  Day 10/90: 6,234 events generated
  Day 20/90: 12,567 events generated
  ...
  Day 90/90: 58,432 events generated
✓ Total events generated: 58,432

Adding anomalous events for testing...
✓ 73 anomalous events added

============================================================
Data Generation Complete!
============================================================
Total Users: 400
Total Events: 58,432
Date Range: 2025-12-08 to 2026-03-07
Average Events/Day: 649
```

### Step 3: Verify the Data

```bash
docker exec -it essl-simulator-mysql mysql -u root -pessl_password essl_db
```

Run some queries:

```sql
-- Total events
SELECT COUNT(*) FROM AccessLogs;

-- Events per day (last 7 days)
SELECT DATE(AccessTime) as date, COUNT(*) as events
FROM AccessLogs
GROUP BY DATE(AccessTime)
ORDER BY date DESC
LIMIT 7;

-- Door usage
SELECT DoorID, COUNT(*) as swipes
FROM AccessLogs
GROUP BY DoorID
ORDER BY swipes DESC;

-- Exit
exit
```

### Step 4: Configure the Data Pipeline

Update your environment variables or `.env` file:

```bash
# Enable eSSL connector
ESSL_ENABLED=true

# Simulator connection (adjust host if needed)
ESSL_DB_HOST=essl-mysql  # Use 'localhost' if running outside Docker
ESSL_DB_PORT=3306        # Use 3307 if connecting from host machine
ESSL_DB_USER=root
ESSL_DB_PASSWORD=essl_password
ESSL_DB_NAME=essl_db
ESSL_TABLE_NAME=AccessLogs

# Poll every 5 minutes
ESSL_POLL_INTERVAL=300
```

### Step 5: Test the Connector

From the main project directory:

```bash
cd backend/simulators/essl_simulator
python test_connector.py
```

**Expected output:**
```
============================================================
eSSL Connector Test
============================================================

Connector Configuration:
  ID: essl_simulator_test
  Type: ConnectorType.CARD_SWIPE
  Host: localhost:3307
  Database: essl_db

============================================================
Test 1: Connection Test
============================================================
✓ Connection successful!

============================================================
Test 2: Sample Data Retrieval
============================================================
✓ Retrieved 5 sample records

Sample record (raw):
  LogID: 1
  UserID: S0001
  CardNo: CARD000001
  AccessTime: 2025-12-08 08:23:15
  DoorID: MAIN_ENTRANCE
  EventType: IN

... (more tests) ...

============================================================
All Tests Passed! ✓
============================================================
```

### Step 6: Start the Data Pipeline

Now your data pipeline can start polling the simulator:

```bash
# Start the ingestion services
docker-compose -f docker-compose.ingestion.yml up -d

# Check Celery Beat logs (should show polling starting)
docker logs celery-beat -f

# You should see:
# [2026-03-07 10:00:00,000: INFO] Starting connector polling cycle
# [2026-03-07 10:00:01,234: INFO] Fetched 127 records from essl_main
```

## Troubleshooting

### MySQL Won't Start

```bash
# Check logs
docker logs essl-simulator-mysql

# Common issue: Port 3307 already in use
lsof -i :3307

# Stop and restart
docker-compose -f docker-compose.simulators.yml down
docker-compose -f docker-compose.simulators.yml up -d essl-mysql
```

### Data Generator Fails

```bash
# Check if MySQL is ready
docker-compose -f docker-compose.simulators.yml ps

# Wait longer and try again
sleep 10
docker-compose -f docker-compose.simulators.yml run --rm essl-data-generator
```

### Connector Can't Connect

**From host machine (localhost:3307):**
```bash
mysql -h localhost -P 3307 -u root -pessl_password essl_db
```

**From Docker container (essl-mysql:3306):**
```bash
docker exec -it essl-simulator-mysql mysql -u root -pessl_password essl_db
```

### No Data in Results

```bash
# Check date range of data
docker exec -it essl-simulator-mysql mysql -u root -pessl_password essl_db -e \
  "SELECT MIN(AccessTime), MAX(AccessTime) FROM AccessLogs;"

# Adjust your fetch_data() since parameter to match the date range
```

## Reset and Regenerate

To start fresh:

```bash
# Stop and remove everything (including data)
docker-compose -f docker-compose.simulators.yml down -v

# Start MySQL
docker-compose -f docker-compose.simulators.yml up -d essl-mysql

# Wait for ready
sleep 30

# Generate fresh data
docker-compose -f docker-compose.simulators.yml run --rm essl-data-generator
```

## Network Configuration

**If running pipeline and simulator on same Docker network:**
```bash
# Add simulator to your network
docker network connect backend_fazri-network essl-simulator-mysql

# Use this in connector config:
ESSL_DB_HOST=essl-simulator-mysql
ESSL_DB_PORT=3306
```

**If running pipeline on host, simulator in Docker:**
```bash
# Use port mapping:
ESSL_DB_HOST=localhost
ESSL_DB_PORT=3307
```

## Next Steps

1. ✅ Simulator running with data
2. ✅ Connector tested and working
3. Configure data pipeline to use simulator
4. Start Celery workers and beat scheduler
5. Monitor logs for polling activity
6. Check Neo4j for graph data being created
7. Use this to test the full MVP pipeline!

---

**Tip:** Keep the simulator running - it's perfect for continuous testing and development without needing real hardware!
