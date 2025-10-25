#!/usr/bin/env python3
"""Update zone capacities to realistic values"""

from neo4j import GraphDatabase

NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Pressword@69"

# Realistic capacities based on zone types
REALISTIC_CAPACITIES = {
    'ADMIN_LOBBY': 50,
    'AUDITORIUM': 300,
    'CAF_01': 250,
    'GYM': 80,
    'HOSTEL_GATE': 30,
    'LAB_101': 40,
    'LAB_102': 35,
    'LAB_306': 30,
    'LIB_ENT': 25,
    'SEM_01': 60,
    'ROOM_A1': 20,
    'ROOM_A2': 20
}

print("🔧 Updating Zone Capacities...")
print("=" * 50)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

with driver.session() as session:
    for zone_id, capacity in REALISTIC_CAPACITIES.items():
        result = session.run("""
            MATCH (z:Zone {zone_id: $zone_id})
            SET z.capacity = $capacity
            RETURN z.zone_id, z.capacity, z.name
        """, {'zone_id': zone_id, 'capacity': capacity})

        record = result.single()
        if record:
            print(f"✅ {record['z.zone_id']:<15} capacity: {capacity:>3} - {record['z.name']}")
        else:
            print(f"⚠️  {zone_id:<15} - Zone not found")

driver.close()

print("=" * 50)
print("✅ Zone capacities updated successfully!")
print("\nNow run: python3 scripts/ingest_real_data.py")
