# Current Status & Next Steps

## ✅ What You Have NOW

- **FastAPI Server**: ✅ Running (main.py on port 8000)
- **Neo4j Database**: ✅ Running (localhost:7687)
- **Zones Created**: ✅ 8 zones with capacity=10
- **Synthetic Data**: ✅ Some SpatialActivity nodes (from migration)
- **Real Data Ingested**: ❌ **NOT YET** - This is why you're getting 0 anomalies!

## 🎯 The Answer to Your Question

**You need to run the ingestion scripts FIRST before you see anomalies.**

Here's why:
1. Your `main.py` API server is **already running** ✅
2. But your **database has no real data yet** ❌
3. The API queries the database → finds nothing → returns 0 anomalies

## 📋 Step-by-Step Workflow

### STEP 1: Check Current State (Optional)
```bash
# Test API right now (will return 0 anomalies)
curl http://localhost:8000/api/v1/anomalies/detect | python3 -m json.tool

# Expected result: "total_count": 0
```

### STEP 2: Ingest Real Data (REQUIRED)
```bash
cd /Users/dinokage/dev/fazri-analyzer/backend

# Option A: Update capacities first (recommended)
python3 scripts/update_zone_capacities.py

# Then ingest real CSV data
python3 scripts/ingest_real_data.py
```

**This will take 2-5 minutes** and output:
```
📋 Ingesting Entities... ✅ 7000
💳 Ingesting Card Swipes... ✅ 32000
📶 Ingesting WiFi Logs... ✅ 32000
📹 Ingesting CCTV Frames... ✅ ~20000
📚 Ingesting Library Checkouts... ✅ 28000
🔬 Ingesting Lab Bookings... ✅ 28000
📊 Creating Occupancy Aggregations... ✅
```

### STEP 3: Check Results (API automatically updates)
```bash
# Your main.py is still running, no need to restart!

# Test API again (will now return hundreds of anomalies)
curl http://localhost:8000/api/v1/anomalies/detect | python3 -m json.tool

# Expected result: "total_count": 400-1600 anomalies
```

### STEP 4: Explore Different Endpoints
```bash
# Get summary
curl http://localhost:8000/api/v1/anomalies/summary | python3 -m json.tool

# Get critical anomalies only
curl http://localhost:8000/api/v1/anomalies/by-severity/critical | python3 -m json.tool

# Get anomalies for specific location
curl http://localhost:8000/api/v1/anomalies/by-location/LAB_305 | python3 -m json.tool

# Interactive docs (open in browser)
open http://localhost:8000/docs
```

## 🔍 Quick Check: Do You Need to Ingest?

Run this diagnostic to see current database state:

```bash
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('neo4j://localhost:7687', auth=('neo4j', 'Pressword@69'))
with driver.session() as s:
    entities = s.run('MATCH (e:Entity) RETURN count(e) as c').single()['c']
    swipes = s.run('MATCH ()-[r:SWIPED_CARD]->() RETURN count(r) as c').single()['c']
    print(f'Entities: {entities}')
    print(f'Card Swipes: {swipes}')
    if entities == 0:
        print('❌ NO DATA YET - Run ingestion script!')
    else:
        print('✅ Data already ingested!')
driver.close()
"
```

## 🚀 Quick Start Commands (Copy-Paste)

```bash
# Navigate to backend
cd /Users/dinokage/dev/fazri-analyzer/backend

# STEP 1: Update capacities (1 second)
python3 scripts/update_zone_capacities.py

# STEP 2: Ingest real data (2-5 minutes)
python3 scripts/ingest_real_data.py

# STEP 3: Check results immediately
curl http://localhost:8000/api/v1/anomalies/detect | python3 -m json.tool | head -50

# STEP 4: Open interactive docs
open http://localhost:8000/docs
```

## 📊 What You'll See After Ingestion

### Before (NOW):
```json
{
  "success": true,
  "data": {
    "anomalies": [],
    "total_count": 0,
    "time_range": "Entire dataset"
  }
}
```

### After (AFTER INGESTION):
```json
{
  "success": true,
  "data": {
    "anomalies": [
      {
        "type": "impossible_travel",
        "severity": "critical",
        "entity_name": "Rohan Kumar",
        "description": "Appeared in AUDITORIUM only 45s after LAB_101",
        "timestamp": "2025-09-15T14:30:00"
      },
      {
        "type": "off_hours_access",
        "severity": "critical",
        "entity_name": "Priya Sharma",
        "description": "Accessed LAB_305 at 2 AM (outside 8-19 hours)",
        "timestamp": "2025-09-12T02:15:00"
      },
      {
        "type": "role_violation",
        "severity": "high",
        "entity_name": "Siddharth Patel",
        "description": "Student accessed faculty-only ROOM_A1",
        "timestamp": "2025-09-18T15:00:00"
      }
    ],
    "total_count": 847
  }
}
```

## ⚠️ Important Notes

1. **You DON'T need to restart main.py** - The API reads from Neo4j each time
2. **Ingestion is a ONE-TIME operation** - Run it once, data stays in DB
3. **If you mess up**, you can clean and re-run:
   ```bash
   # Clean all data
   python3 -c "
   from neo4j import GraphDatabase
   driver = GraphDatabase.driver('neo4j://localhost:7687', auth=('neo4j', 'Pressword@69'))
   with driver.session() as s:
       s.run('MATCH (n) DETACH DELETE n')
   driver.close()
   print('✅ Database cleaned')
   "

   # Then re-run migration + ingestion
   python3 migrations/add_spatial_zones.py
   python3 scripts/ingest_real_data.py
   ```

## 🎯 TL;DR - Just Run This

```bash
cd /Users/dinokage/dev/fazri-analyzer/backend
python3 scripts/update_zone_capacities.py && \
python3 scripts/ingest_real_data.py && \
echo "✅ Done! Now check: curl http://localhost:8000/api/v1/anomalies/detect"
```

Then open your browser to: **http://localhost:8000/docs** and test all endpoints!
