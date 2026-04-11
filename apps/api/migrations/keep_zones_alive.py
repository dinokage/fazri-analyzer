#!/usr/bin/env python3
"""
Zone Occupancy Updater - Keeps zone data fresh
Runs continuously, updating every 5 minutes
No external dependencies - uses only stdlib
"""

import os
import time
import random
from datetime import datetime
from neo4j import GraphDatabase

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# Zone configurations
ZONES = {
    "ADMIN_LOBBY": {"capacity": 50, "base_occupancy": 15, "variance": 10},
    "AUDITORIUM": {"capacity": 500, "base_occupancy": 480, "variance": 15},  # Overcrowded
    "CAF_01": {"capacity": 200, "base_occupancy": 185, "variance": 10},      # Overcrowded
    "GYM": {"capacity": 80, "base_occupancy": 25, "variance": 15},
    "HOSTEL_GATE": {"capacity": 30, "base_occupancy": 8, "variance": 5},
    "LAB_101": {"capacity": 40, "base_occupancy": 12, "variance": 8},
    "LAB_102": {"capacity": 40, "base_occupancy": 15, "variance": 8},
    "LAB_305": {"capacity": 35, "base_occupancy": 10, "variance": 7},
    "LIB_ENT": {"capacity": 25, "base_occupancy": 8, "variance": 5},
    "SEM_01": {"capacity": 100, "base_occupancy": 35, "variance": 20},
}

UPDATE_INTERVAL = 300  # 5 minutes in seconds


def get_status(occupancy_rate: float) -> str:
    """Determine zone status based on occupancy rate."""
    if occupancy_rate >= 0.9:
        return "Full"
    elif occupancy_rate >= 0.7:
        return "High"
    elif occupancy_rate >= 0.4:
        return "Medium"
    else:
        return "Low"


def update_zones():
    """Update all zone occupancy data in Neo4j."""
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] Updating zone occupancy...")
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            for zone_id, config in ZONES.items():
                # Calculate occupancy with some randomness
                variance = random.randint(-config["variance"], config["variance"])
                current = max(0, min(config["capacity"], config["base_occupancy"] + variance))
                
                occupancy_rate = current / config["capacity"]
                status = get_status(occupancy_rate)
                
                # Update the zone
                session.run("""
                    MATCH (z:Zone {zone_id: $zone_id})
                    SET z.current_occupancy = $current,
                        z.occupancy_rate = $rate,
                        z.status = $status,
                        z.last_updated = datetime()
                """, zone_id=zone_id, current=current, rate=occupancy_rate, status=status)
                
                print(f"  {zone_id}: {current}/{config['capacity']} ({occupancy_rate:.1%}) - {status}")
        
        driver.close()
        print(f"[{timestamp}] Update complete!\n")
        
    except Exception as e:
        print(f"[{timestamp}] ERROR: {e}\n")


def main():
    """Main loop - runs forever, updating every 5 minutes."""
    print("=" * 50)
    print("Zone Occupancy Updater Started")
    print(f"Update interval: {UPDATE_INTERVAL} seconds ({UPDATE_INTERVAL // 60} minutes)")
    print("=" * 50)
    print()
    
    # Run immediately on start
    update_zones()
    
    # Then loop forever
    while True:
        time.sleep(UPDATE_INTERVAL)
        update_zones()


if __name__ == "__main__":
    main()
