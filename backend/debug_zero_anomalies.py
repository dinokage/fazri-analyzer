#!/usr/bin/env python3
"""Debug why we're getting zero anomalies after ingestion"""

from neo4j import GraphDatabase
from datetime import datetime

NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Pressword@69"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 80)
print("DEBUGGING ZERO ANOMALIES ISSUE")
print("=" * 80)

with driver.session() as session:
    # 1. Check if data exists
    print("\n1. DATA EXISTENCE CHECK")
    print("-" * 80)

    entities = session.run("MATCH (e:Entity) RETURN count(e) as count").single()['count']
    print(f"✓ Entities: {entities}")

    zones = session.run("MATCH (z:Zone) RETURN count(z) as count").single()['count']
    print(f"✓ Zones: {zones}")

    swipes = session.run("MATCH ()-[r:SWIPED_CARD]->() RETURN count(r) as count").single()['count']
    print(f"✓ Card Swipes: {swipes}")

    wifi = session.run("MATCH ()-[r:CONNECTED_TO_WIFI]->() RETURN count(r) as count").single()['count']
    print(f"✓ WiFi Connections: {wifi}")

    spatial = session.run("MATCH (sa:SpatialActivity) RETURN count(sa) as count").single()['count']
    print(f"✓ Spatial Activities: {spatial}")

    if entities == 0 or swipes == 0:
        print("\n❌ NO DATA FOUND! Ingestion didn't work.")
        print("   Run: python3 scripts/ingest_real_data.py")
        exit(1)

    # 2. Check zone capacities
    print("\n2. ZONE CAPACITY CHECK")
    print("-" * 80)

    zone_caps = session.run("""
        MATCH (z:Zone)
        RETURN z.zone_id as zone_id, z.capacity as capacity
        ORDER BY z.zone_id
    """)

    low_capacity_zones = []
    for rec in zone_caps:
        capacity = rec['capacity']
        status = "⚠️  LOW" if capacity <= 10 else "✓"
        print(f"{status} {rec['zone_id']:<15} capacity: {capacity}")
        if capacity <= 10:
            low_capacity_zones.append(rec['zone_id'])

    # 3. Check for potential overcrowding in raw data
    print("\n3. RAW DATA OVERCROWDING CHECK")
    print("-" * 80)

    overcrowding_check = session.run("""
        MATCH (e:Entity)-[s:SWIPED_CARD]->(z:Zone)
        WITH z,
             date(s.timestamp) as activity_date,
             s.timestamp.hour as hour,
             count(DISTINCT e) as unique_people
        WHERE unique_people > z.capacity
        RETURN z.zone_id as zone_id,
               z.capacity as capacity,
               activity_date,
               hour,
               unique_people
        ORDER BY unique_people DESC
        LIMIT 10
    """)

    overcrowding_found = list(overcrowding_check)
    if overcrowding_found:
        print(f"✓ Found {len(overcrowding_found)} potential overcrowding instances:")
        for rec in overcrowding_found[:5]:
            print(f"  - {rec['zone_id']}: {rec['unique_people']} people (capacity {rec['capacity']}) on {rec['activity_date']} hour {rec['hour']}")
    else:
        print("❌ NO overcrowding found in raw card swipe data!")
        print("   This means either:")
        print("   - Zone capacities are too high")
        print("   - Or occupancy never exceeds capacity")

    # 4. Check aggregated spatial activities
    print("\n4. SPATIAL ACTIVITY AGGREGATION CHECK")
    print("-" * 80)

    spatial_overcrowding = session.run("""
        MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
        WHERE sa.occupancy > z.capacity
        RETURN z.zone_id as zone_id,
               z.capacity as capacity,
               sa.occupancy as occupancy,
               sa.timestamp as timestamp
        ORDER BY sa.occupancy DESC
        LIMIT 10
    """)

    spatial_over = list(spatial_overcrowding)
    if spatial_over:
        print(f"✓ Found {len(spatial_over)} overcrowding in SpatialActivity:")
        for rec in spatial_over[:5]:
            print(f"  - {rec['zone_id']}: occupancy {rec['occupancy']} > capacity {rec['capacity']}")
    else:
        print("❌ NO overcrowding in SpatialActivity aggregations!")

    # 5. Check if anomaly detection query works
    print("\n5. ANOMALY DETECTION QUERY TEST")
    print("-" * 80)

    # Get time range
    time_range = session.run("""
        MATCH (sa:SpatialActivity)
        WHERE sa.timestamp IS NOT NULL
        RETURN min(sa.timestamp) as start_time, max(sa.timestamp) as end_time
    """).single()

    if time_range and time_range['start_time']:
        start_time = time_range['start_time']
        end_time = time_range['end_time']

        if hasattr(start_time, 'to_native'):
            start_time = start_time.to_native()
        if hasattr(end_time, 'to_native'):
            end_time = end_time.to_native()

        print(f"✓ Time range: {start_time} to {end_time}")

        # Run the actual overcrowding query
        anomaly_query = session.run("""
            MATCH (z:Zone)<-[:OCCURRED_IN]-(sa:SpatialActivity)
            WHERE sa.timestamp >= datetime($start_time)
            AND sa.timestamp <= datetime($end_time)
            AND sa.occupancy > 0
            WITH z, sa,
                 date(sa.timestamp) as activity_date,
                 sa.hour as hour
            WHERE sa.occupancy > z.capacity
            RETURN z.zone_id as zone_id,
                   z.name as zone_name,
                   z.capacity as capacity,
                   activity_date,
                   hour,
                   max(sa.occupancy) as max_occupancy,
                   count(sa) as incident_count
            ORDER BY max_occupancy DESC
        """, {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        })

        anomaly_results = list(anomaly_query)
        if anomaly_results:
            print(f"✓ Anomaly query returned {len(anomaly_results)} results!")
            for rec in anomaly_results[:5]:
                print(f"  - {rec['zone_id']} on {rec['activity_date']} hour {rec['hour']}: {rec['max_occupancy']} > {rec['capacity']}")
        else:
            print("❌ Anomaly query returned ZERO results!")
            print("   Checking why...")

            # Debug: Check each condition
            debug1 = session.run("""
                MATCH (sa:SpatialActivity)
                RETURN count(sa) as total
            """).single()['total']
            print(f"   - Total SpatialActivity nodes: {debug1}")

            debug2 = session.run("""
                MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
                RETURN count(sa) as with_zone
            """).single()['with_zone']
            print(f"   - SpatialActivity with OCCURRED_IN relationship: {debug2}")

            debug3 = session.run("""
                MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
                WHERE sa.timestamp IS NOT NULL
                RETURN count(sa) as with_timestamp
            """).single()['with_timestamp']
            print(f"   - SpatialActivity with timestamp: {debug3}")

            debug4 = session.run("""
                MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
                WHERE sa.timestamp IS NOT NULL AND sa.occupancy > 0
                RETURN count(sa) as with_occupancy
            """).single()['with_occupancy']
            print(f"   - SpatialActivity with occupancy > 0: {debug4}")

            debug5 = session.run("""
                MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
                WHERE sa.timestamp IS NOT NULL
                AND sa.occupancy > 0
                AND sa.occupancy > z.capacity
                RETURN count(sa) as overcrowding
            """).single()['overcrowding']
            print(f"   - SpatialActivity where occupancy > capacity: {debug5}")

            if debug5 == 0:
                print("\n   ROOT CAUSE: No SpatialActivity records exceed zone capacity!")
                print("   Checking max occupancy vs capacity for each zone:")

                capacity_analysis = session.run("""
                    MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
                    RETURN z.zone_id as zone_id,
                           z.capacity as capacity,
                           max(sa.occupancy) as max_occupancy,
                           avg(sa.occupancy) as avg_occupancy
                    ORDER BY z.zone_id
                """)

                for rec in capacity_analysis:
                    max_occ = rec['max_occupancy'] or 0
                    cap = rec['capacity'] or 0
                    status = "✓ OVER" if max_occ > cap else "❌ UNDER"
                    print(f"   {status} {rec['zone_id']:<15} max:{max_occ:>4} vs cap:{cap:>4}")

    # 6. Check entity-level anomalies
    print("\n6. ENTITY-LEVEL ANOMALY CHECK")
    print("-" * 80)

    # Check for off-hours access
    off_hours = session.run("""
        MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone)
        WHERE z.zone_id IN ['LAB_101', 'LAB_305', 'LAB_102']
        AND (r.timestamp.hour < 7 OR r.timestamp.hour >= 21)
        RETURN count(*) as count
    """).single()['count']
    print(f"{'✓' if off_hours > 0 else '❌'} Off-hours lab access: {off_hours}")

    # Check for role violations
    role_violations = session.run("""
        MATCH (e:Entity {role: 'student'})-[r:SWIPED_CARD]->(z:Zone)
        WHERE z.zone_id IN ['ROOM_A1', 'ROOM_A2']
        RETURN count(*) as count
    """).single()['count']
    print(f"{'✓' if role_violations > 0 else '❌'} Role violations (students in faculty rooms): {role_violations}")

    # Check for department violations
    dept_violations = session.run("""
        MATCH (e:Entity)-[r:SWIPED_CARD]->(z:Zone {zone_id: 'LAB_305'})
        WHERE e.role = 'student'
        AND NOT e.department IN ['ECE', 'EEE', 'Physics']
        RETURN count(*) as count
    """).single()['count']
    print(f"{'✓' if dept_violations > 0 else '❌'} Department violations: {dept_violations}")

    # Check for impossible travel
    impossible_travel = session.run("""
        MATCH (e:Entity)-[r1:SWIPED_CARD]->(z1:Zone)
        MATCH (e)-[r2:SWIPED_CARD]->(z2:Zone)
        WHERE r2.timestamp > r1.timestamp
        AND z1.zone_id <> z2.zone_id
        WITH e, z1, z2, r1, r2,
             duration.between(r1.timestamp, r2.timestamp).seconds as time_diff
        WHERE time_diff < 120 AND time_diff > 0
        RETURN count(*) as count
        LIMIT 1
    """).single()['count']
    print(f"{'✓' if impossible_travel > 0 else '❌'} Impossible travel (< 2 min between zones): {impossible_travel}")

print("\n" + "=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)

driver.close()
