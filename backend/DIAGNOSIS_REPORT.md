# Anomaly Detection Issue - Root Cause Analysis

## Problems Identified

### Problem 1: Low Capacity Values ❌
Your migration script set all zone capacities to **10**:
```python
{"zone_id": "ADMIN_LOBBY", "capacity": 10}  # Should be 50
{"zone_id": "AUDITORIUM", "capacity": 10}    # Should be 300
{"zone_id": "LAB_101", "capacity": 10}       # Should be 40
```

But synthetic patterns are generating values like 35, 40, 280 which SHOULD trigger anomalies.

### Problem 2: Real Data Not Ingested ❌❌❌ **CRITICAL**
Your actual data from CSV files is **NOT in the graph database**:
- ✅ CSV files exist: 32k card swipes, 28k CCTV frames, 28k bookings
- ❌ **Not linked to zones in Neo4j**
- ❌ **Not linked to entities in Neo4j**

The migration only created:
- 8 zones
- Synthetic SpatialActivity data (last 30 days, hourly patterns)
- NO real card swipes
- NO real WiFi associations
- NO real CCTV frames
- NO entity activities

### Problem 3: Missing Entity Relationships ❌
Entities (students/staff) are not linked to their activities:
- No `(Entity)-[:SWIPED_CARD]->(Zone)` relationships
- No `(Entity)-[:CONNECTED_TO_WIFI]->(AccessPoint)` relationships
- No `(Entity)-[:DETECTED_IN]->(Zone)` CCTV relationships

## Why API Returns Empty

The anomaly detection service expects **actual activity data** to be linked to zones and entities, but only synthetic data exists. Even though synthetic data might exceed capacity, there could be:

1. **Timing issues**: Synthetic data might be old (30 days back)
2. **Pattern issues**: Patterns stay within limits
3. **Query issues**: Anomaly queries might not match the data format

## Solution Required

You need to:

1. ✅ **Ingest real CSV data** into Neo4j graph
2. ✅ **Create Entity nodes** from `student_staff_profiles.csv`
3. ✅ **Link card swipes** to entities and zones
4. ✅ **Link WiFi logs** to entities and zones
5. ✅ **Link CCTV frames** to entities and zones
6. ✅ **Create time-based activity aggregations** for anomaly detection
7. ✅ **Add entity-level anomaly detection**

## Expected Graph Structure

```
(Entity:Person {entity_id, name, role, department})
    |
    ├─[:SWIPED_CARD {timestamp}]─>(Zone {zone_id, capacity})
    ├─[:CONNECTED_TO_WIFI {timestamp}]─>(AccessPoint {ap_id})
    └─[:DETECTED_IN {timestamp, face_id}]─>(Zone)

(Zone)<─[:OCCURRED_IN]─(SpatialActivity {timestamp, occupancy, hour})
```

## Entity-Level Anomalies to Detect

1. **Off-hours Access**: Student in LAB_305 at 2 AM
2. **Role Violations**: Student in ROOM_A1 (faculty only)
3. **Department Violations**: CIVIL student in LAB_305 (ECE restricted)
4. **Impossible Travel**: Same entity in 2 zones 2 minutes apart
5. **Excessive Access**: Entity entering same zone 10 times in an hour
6. **Multi-modal Mismatches**: Card swipe location ≠ WiFi location
7. **Identity Fraud**: Face_id mismatch with card_id
