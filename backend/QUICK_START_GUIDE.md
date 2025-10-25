# Quick Start Guide - Fix Anomaly Detection

## Problem Summary

✅ **DIAGNOSED**: Your API returns zero anomalies because:
1. Zones have low capacity (10 instead of realistic values)
2. **Real CSV data is NOT in the Neo4j graph database** ❌
3. No entity-level tracking (entities not linked to their activities)

## Solution Steps

### Step 1: Ingest Real Data into Neo4j

Run the data ingestion script to load your actual CSV data:

```bash
cd /Users/dinokage/dev/fazri-analyzer/backend
python3 scripts/ingest_real_data.py
```

This will:
- ✅ Create 7,000 Entity nodes (students/faculty/staff)
- ✅ Link 32,000 card swipes to entities and zones
- ✅ Link 32,000 WiFi logs to entities and zones
- ✅ Link 28,000 CCTV frames to entities and zones
- ✅ Link 28,000 library checkouts
- ✅ Link 28,000 lab bookings
- ✅ Create hourly occupancy aggregations for anomaly detection

**Expected Output:**
```
📋 Ingesting Entities... ✅ 7000
💳 Ingesting Card Swipes... ✅ 32000
📶 Ingesting WiFi Logs... ✅ 32000
📹 Ingesting CCTV Frames... ✅ 28000
📚 Ingesting Library Checkouts... ✅ 28000
🔬 Ingesting Lab Bookings... ✅ 28000
📊 Creating Occupancy Aggregations... ✅
```

### Step 2: Update Zone Capacities (Optional but Recommended)

The migration created zones with capacity=10. Update to realistic values:

```cypher
// Run in Neo4j Browser
MATCH (z:Zone {zone_id: 'ADMIN_LOBBY'}) SET z.capacity = 50;
MATCH (z:Zone {zone_id: 'AUDITORIUM'}) SET z.capacity = 300;
MATCH (z:Zone {zone_id: 'CAF_01'}) SET z.capacity = 250;
MATCH (z:Zone {zone_id: 'GYM'}) SET z.capacity = 80;
MATCH (z:Zone {zone_id: 'HOSTEL_GATE'}) SET z.capacity = 30;
MATCH (z:Zone {zone_id: 'LAB_101'}) SET z.capacity = 40;
MATCH (z:Zone {zone_id: 'LAB_102'}) SET z.capacity = 35;
MATCH (z:Zone {zone_id: 'LAB_306'}) SET z.capacity = 30;
MATCH (z:Zone {zone_id: 'LIB_ENT'}) SET z.capacity = 25;
```

Or run this Python script (create it):
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "Pressword@69"))

capacities = {
    'ADMIN_LOBBY': 50, 'AUDITORIUM': 300, 'CAF_01': 250, 'GYM': 80,
    'HOSTEL_GATE': 30, 'LAB_101': 40, 'LAB_102': 35, 'LAB_306': 30,
    'LIB_ENT': 25, 'SEM_01': 60, 'ROOM_A1': 20, 'ROOM_A2': 20
}

with driver.session() as session:
    for zone_id, capacity in capacities.items():
        session.run("MATCH (z:Zone {zone_id: $zone_id}) SET z.capacity = $capacity",
                   {'zone_id': zone_id, 'capacity': capacity})
        print(f"✅ Updated {zone_id} capacity to {capacity}")

driver.close()
```

### Step 3: Test Anomaly Detection

Now test the API endpoints:

```bash
# 1. Get all anomalies
curl -s http://localhost:8000/api/v1/anomalies/detect | python3 -m json.tool

# 2. Get anomaly summary
curl -s http://localhost:8000/api/v1/anomalies/summary | python3 -m json.tool

# 3. Get anomalies by severity
curl -s http://localhost:8000/api/v1/anomalies/by-severity/critical | python3 -m json.tool

# 4. Get anomalies by location
curl -s http://localhost:8000/api/v1/anomalies/by-location/LAB_305 | python3 -m json.tool
```

## Entity-Level Anomalies Now Detected

After ingestion, you'll see these entity-level anomalies:

### 1. Off-Hours Access 🕐
**Example**: Student E100123 accessed LAB_305 at 2 AM
- **Severity**: CRITICAL (restricted labs), HIGH (others)
- **Query**:
```cypher
MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone {zone_id: 'LAB_305'})
WHERE r.timestamp.hour NOT IN range(8, 18)
RETURN e.name, r.timestamp, r.timestamp.hour
```

### 2. Role Violations 👥
**Example**: Student accessed ROOM_A1 (faculty-only)
- **Severity**: HIGH
- **Query**:
```cypher
MATCH (e:Entity {role: 'student'})-[:SWIPED_CARD]->(z:Zone)
WHERE z.zone_id IN ['ROOM_A1', 'ROOM_A2']
RETURN e.name, e.entity_id, z.zone_id
```

### 3. Department Violations 🏫
**Example**: CIVIL student accessed LAB_305 (ECE/EEE only)
- **Severity**: HIGH
- **Query**:
```cypher
MATCH (e:Entity)-[:SWIPED_CARD]->(z:Zone {zone_id: 'LAB_305'})
WHERE e.role = 'student'
AND NOT e.department IN ['ECE', 'EEE', 'Physics']
RETURN e.name, e.department, e.entity_id
```

### 4. Impossible Travel ⚡
**Example**: Same person in 2 zones 90 seconds apart
- **Severity**: CRITICAL
- **Query**:
```cypher
MATCH (e:Entity)-[r1:SWIPED_CARD]->(z1:Zone)
MATCH (e)-[r2:SWIPED_CARD]->(z2:Zone)
WHERE r2.timestamp > r1.timestamp
AND z1 <> z2
WITH e, z1, z2, r1, r2,
     duration.between(r1.timestamp, r2.timestamp).seconds as time_diff
WHERE time_diff < 120
RETURN e.name, z1.zone_id, z2.zone_id, time_diff
```

### 5. Multi-Modal Mismatches 📍
**Example**: Card swipe at LAB_101 but WiFi at AUDITORIUM
- **Severity**: MEDIUM
- **Indicates**: Tailgating, card sharing, or identity fraud

### 6. Curfew Violations 🌙
**Example**: Hostel entry after 23:00 (11 PM)
- **Severity**: MEDIUM
- **Query**:
```cypher
MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone {zone_id: 'HOSTEL_GATE'})
WHERE r.timestamp.hour >= 23
RETURN e.name, r.timestamp
ORDER BY r.timestamp DESC
```

### 7. Excessive Access 🔁
**Example**: 15 accesses to same zone in 1 hour
- **Severity**: MEDIUM
- **Indicates**: Card sharing or bot behavior

### 8. Booking No-Shows ❌
**Example**: Booked LAB_101 but didn't attend
- **Severity**: LOW
- **Impact**: Resource waste

## Expected Anomaly Counts

Based on your dataset (32k card swipes across zones):

| Type | Expected Count | Severity |
|------|----------------|----------|
| Off-hours access | 50-200 | CRITICAL/HIGH |
| Role violations | 10-50 | HIGH |
| Department violations | 5-20 | HIGH |
| Impossible travel | 100-500 | CRITICAL |
| Location mismatches | 50-200 | MEDIUM |
| Curfew violations | 20-100 | MEDIUM |
| Excessive access | 10-50 | MEDIUM |
| Booking no-shows | 200-500 | LOW |

**Total Expected**: 445-1,620 anomalies

## Verification Queries

### Check Data Ingestion Success

```cypher
// 1. Count entities
MATCH (e:Entity) RETURN count(e) as entities;
// Expected: ~7000

// 2. Count card swipes
MATCH ()-[r:SWIPED_CARD]->() RETURN count(r) as swipes;
// Expected: ~32000

// 3. Count WiFi connections
MATCH ()-[r:CONNECTED_TO_WIFI]->() RETURN count(r) as wifi;
// Expected: ~32000

// 4. Count CCTV detections
MATCH ()-[r:DETECTED_IN]->() RETURN count(r) as cctv;
// Expected: ~15000-20000 (only frames with faces)

// 5. Check zones with capacity
MATCH (z:Zone) RETURN z.zone_id, z.capacity ORDER BY z.zone_id;

// 6. Sample entity activities
MATCH (e:Entity)-[r]->(z:Zone)
RETURN e.name, e.role, type(r), z.zone_id, r.timestamp
LIMIT 10;
```

### Find Specific Anomalies

```cypher
// Students in faculty rooms
MATCH (e:Entity {role: 'student'})-[r:SWIPED_CARD]->(z:Zone)
WHERE z.zone_id IN ['ROOM_A1', 'ROOM_A2']
RETURN e.name, z.zone_id, r.timestamp
LIMIT 10;

// Late night lab access
MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone)
WHERE z.zone_id IN ['LAB_101', 'LAB_305']
AND r.timestamp.hour NOT IN range(8, 20)
RETURN e.name, z.zone_id, r.timestamp.hour, r.timestamp
ORDER BY r.timestamp DESC
LIMIT 10;

// Wrong department in restricted lab
MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone {zone_id: 'LAB_305'})
WHERE NOT e.department IN ['ECE', 'EEE', 'Physics']
RETURN e.name, e.department, r.timestamp
LIMIT 10;
```

## Troubleshooting

### If still getting zero anomalies:

1. **Check if data was ingested**:
   ```bash
   python3 diagnose_anomalies.py
   ```

2. **Check API logs**:
   ```bash
   tail -f /path/to/api/logs
   ```

3. **Verify Neo4j connection**:
   ```bash
   curl http://localhost:7474
   ```

4. **Test anomaly detection directly**:
   ```python
   from services.anomaly_detection import AnomalyDetectionService

   service = AnomalyDetectionService("neo4j://localhost:7687", "neo4j", "Pressword@69")
   anomalies = service.detect_all_anomalies()
   print(f"Found {len(anomalies)} anomalies")
   for a in anomalies[:5]:
       print(f"- {a['type']}: {a['description']}")
   ```

## Architecture After Ingestion

```
Neo4j Graph Database:
├── Entity nodes (7,000)
│   ├── Students (5,601)
│   ├── Faculty (681)
│   └── Staff (718)
├── Zone nodes (12)
│   └── Each with realistic capacity
├── Relationships:
│   ├── SWIPED_CARD (32,000) → Entity to Zone
│   ├── CONNECTED_TO_WIFI (32,000) → Entity to Zone
│   ├── DETECTED_IN (20,000) → Entity to Zone
│   ├── CHECKED_OUT_BOOK (28,000) → Entity to Book
│   ├── BOOKED_ROOM (28,000) → Entity to Zone
│   └── OCCURRED_IN → SpatialActivity to Zone
└── SpatialActivity nodes (aggregated hourly occupancy)
```

## Next Steps

1. ✅ Run `python3 scripts/ingest_real_data.py`
2. ✅ Update zone capacities (optional)
3. ✅ Test API: `curl http://localhost:8000/api/v1/anomalies/detect`
4. ✅ View in browser: `http://localhost:8000/docs`
5. ✅ Create dashboards/visualizations
6. ✅ Set up alerts for critical anomalies

## Files Created

- `/backend/DIAGNOSIS_REPORT.md` - Root cause analysis
- `/backend/scripts/ingest_real_data.py` - Data ingestion script
- `/backend/services/entity_anomaly_detection.py` - Entity-level anomaly detection
- `/backend/QUICK_START_GUIDE.md` - This file
- `/backend/ZONES_AND_ANOMALIES.md` - Comprehensive anomaly documentation
