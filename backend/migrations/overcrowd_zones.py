#!/usr/bin/env python3
"""
Quick script to set high occupancy for specific zones.
This simulates overcrowded conditions for testing.
"""

from neo4j import GraphDatabase
from datetime import datetime
import os

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def overcrowd_zones():
    """Set specific zones to high/overcrowded occupancy levels"""
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # Zones to overcrowd with their target occupancy
    # Format: zone_id -> (target_occupancy, capacity)
    overcrowded_zones = {
        "CAF_01": (185, 200),      # 92.5% - Nearly full cafeteria
        "AUDITORIUM": (480, 500),  # 96% - Packed auditorium (event happening)
    }
    
    now = datetime.now()
    timestamp = now.replace(second=0, microsecond=0)
    
    print("🔥 Setting overcrowded zones...")
    print(f"   Timestamp: {timestamp.isoformat()}")
    print()
    
    with driver.session() as session:
        for zone_id, (occupancy, capacity) in overcrowded_zones.items():
            rate = (occupancy / capacity) * 100
            
            # Update zone's current occupancy
            result = session.run("""
                MATCH (z:Zone {zone_id: $zone_id})
                SET z.current_occupancy = $occupancy,
                    z.last_updated = datetime($timestamp)
                RETURN z.name as name, z.capacity as capacity
            """, {
                'zone_id': zone_id,
                'occupancy': occupancy,
                'timestamp': timestamp.isoformat()
            })
            
            record = result.single()
            if record:
                print(f"   🔴 {record['name']}")
                print(f"      Zone ID: {zone_id}")
                print(f"      Occupancy: {occupancy}/{capacity} ({rate:.1f}%)")
                print(f"      Status: {'FULL' if rate >= 90 else 'CROWDED'}")
                print()
            else:
                print(f"   ⚠️  Zone {zone_id} not found!")
    
    driver.close()
    print("✅ Done! Refresh your dashboard to see the changes.")

if __name__ == "__main__":
    overcrowd_zones()
