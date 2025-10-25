#!/usr/bin/env python3
"""Diagnostic script to troubleshoot why anomalies are not being detected"""

from neo4j import GraphDatabase
from datetime import datetime

NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Pressword@69"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 80)
print("ANOMALY DETECTION DIAGNOSTIC TOOL")
print("=" * 80)

with driver.session() as session:
    # 1. Check if zones exist
    print("\n1. CHECKING ZONES...")
    zones_result = session.run("""
        MATCH (z:Zone)
        RETURN z.zone_id as zone_id, z.capacity as capacity, z.name as name
        ORDER BY z.zone_id
    """)
    zones = list(zones_result)
    print(f"   Found {len(zones)} zones:")
    for z in zones:
        print(f"   - {z['zone_id']}: capacity={z['capacity']}, name={z['name']}")

    if len(zones) == 0:
        print("   ❌ NO ZONES FOUND! Run the migration first.")
        exit(1)

    # 2. Check if SpatialActivity exists
    print("\n2. CHECKING SPATIAL ACTIVITIES...")
    activity_result = session.run("""
        MATCH (sa:SpatialActivity)
        RETURN count(sa) as total_activities,
               min(sa.timestamp) as earliest,
               max(sa.timestamp) as latest
    """)
    activity_record = activity_result.single()
    print(f"   Total activities: {activity_record['total_activities']}")
    if activity_record['total_activities'] > 0:
        print(f"   Earliest: {activity_record['earliest']}")
        print(f"   Latest: {activity_record['latest']}")
    else:
        print("   ❌ NO ACTIVITIES FOUND! Run the migration first.")
        exit(1)

    # 3. Check if OCCURRED_IN relationships exist
    print("\n3. CHECKING OCCURRED_IN RELATIONSHIPS...")
    rel_result = session.run("""
        MATCH (sa:SpatialActivity)-[r:OCCURRED_IN]->(z:Zone)
        RETURN count(r) as total_relationships
    """)
    rel_count = rel_result.single()['total_relationships']
    print(f"   Total OCCURRED_IN relationships: {rel_count}")

    if rel_count == 0:
        print("   ❌ NO RELATIONSHIPS FOUND! Data is disconnected.")
        exit(1)

    # 4. Sample some activities with their zones
    print("\n4. SAMPLE DATA (first 10 activities)...")
    sample_result = session.run("""
        MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
        RETURN z.zone_id as zone_id,
               z.capacity as capacity,
               sa.occupancy as occupancy,
               sa.timestamp as timestamp,
               sa.hour as hour
        ORDER BY sa.timestamp DESC
        LIMIT 10
    """)
    print(f"   {'Zone':<15} {'Capacity':<10} {'Occupancy':<10} {'Timestamp':<25} {'Hour'}")
    print(f"   {'-'*15} {'-'*10} {'-'*10} {'-'*25} {'-'*4}")
    for rec in sample_result:
        print(f"   {rec['zone_id']:<15} {rec['capacity']:<10} {rec['occupancy']:<10} {str(rec['timestamp']):<25} {rec['hour']}")

    # 5. Check for potential overcrowding
    print("\n5. CHECKING FOR OVERCROWDING (occupancy > capacity)...")
    overcrowding_result = session.run("""
        MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
        WHERE sa.occupancy > z.capacity
        RETURN z.zone_id as zone_id,
               z.capacity as capacity,
               sa.occupancy as occupancy,
               sa.timestamp as timestamp,
               count(*) as overcrowding_count
        ORDER BY overcrowding_count DESC
        LIMIT 10
    """)
    overcrowding_records = list(overcrowding_result)

    if len(overcrowding_records) == 0:
        print("   ❌ NO OVERCROWDING FOUND!")
        print("\n   Let's check the distribution of occupancy values:")

        dist_result = session.run("""
            MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
            RETURN z.zone_id as zone_id,
                   z.capacity as capacity,
                   min(sa.occupancy) as min_occ,
                   max(sa.occupancy) as max_occ,
                   avg(sa.occupancy) as avg_occ,
                   count(sa) as data_points
            ORDER BY z.zone_id
        """)

        print(f"\n   {'Zone':<15} {'Capacity':<10} {'Min Occ':<10} {'Max Occ':<10} {'Avg Occ':<10} {'Points'}")
        print(f"   {'-'*15} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*6}")
        for rec in dist_result:
            print(f"   {rec['zone_id']:<15} {rec['capacity']:<10} {rec['min_occ']:<10} {rec['max_occ']:<10} {rec['avg_occ']:<10.1f} {rec['data_points']}")

            # Highlight the problem
            if rec['max_occ'] > rec['capacity']:
                print(f"   ✅ Zone {rec['zone_id']} HAS overcrowding: max={rec['max_occ']} > capacity={rec['capacity']}")
            else:
                print(f"   ⚠️  Zone {rec['zone_id']} NO overcrowding: max={rec['max_occ']} <= capacity={rec['capacity']}")
    else:
        print(f"   ✅ Found {len(overcrowding_records)} zones with overcrowding:")
        for rec in overcrowding_records:
            print(f"   - {rec['zone_id']}: {rec['overcrowding_count']} instances")

    # 6. Test the actual anomaly detection query
    print("\n6. TESTING ANOMALY DETECTION QUERY...")

    # Get dataset range
    range_result = session.run("""
        MATCH (sa:SpatialActivity)
        RETURN min(sa.timestamp) as start_time, max(sa.timestamp) as end_time
    """)
    range_rec = range_result.single()
    start_time = range_rec['start_time']
    end_time = range_rec['end_time']

    # Convert to native Python datetime if needed
    if hasattr(start_time, 'to_native'):
        start_time = start_time.to_native()
    if hasattr(end_time, 'to_native'):
        end_time = end_time.to_native()

    print(f"   Time range: {start_time} to {end_time}")

    # Run the actual overcrowding query from the service
    anomaly_query_result = session.run("""
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
               avg(sa.occupancy) as avg_occupancy,
               count(sa) as incident_count
        ORDER BY max_occupancy DESC
    """, {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat()
    })

    anomaly_records = list(anomaly_query_result)
    print(f"   Anomaly query returned {len(anomaly_records)} results")

    if len(anomaly_records) > 0:
        print("\n   ✅ ANOMALIES DETECTED:")
        for rec in anomaly_records[:5]:
            print(f"   - {rec['zone_id']} on {rec['activity_date']} at hour {rec['hour']}")
            print(f"     Max occupancy: {rec['max_occupancy']}, Capacity: {rec['capacity']}")
    else:
        print("\n   ❌ NO ANOMALIES DETECTED BY QUERY")

        # Debug: Check if the WHERE clause is filtering everything out
        print("\n   Debugging: Checking without capacity filter...")
        debug_result = session.run("""
            MATCH (z:Zone)<-[:OCCURRED_IN]-(sa:SpatialActivity)
            WHERE sa.timestamp >= datetime($start_time)
            AND sa.timestamp <= datetime($end_time)
            AND sa.occupancy > 0
            RETURN count(*) as total_matching_activities
        """, {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        })
        debug_count = debug_result.single()['total_matching_activities']
        print(f"   Activities matching time range and occupancy>0: {debug_count}")

        # Check if capacity property exists
        print("\n   Checking capacity property on zones...")
        capacity_check = session.run("""
            MATCH (z:Zone)
            RETURN z.zone_id as zone_id,
                   z.capacity as capacity,
                   z.capacity IS NOT NULL as has_capacity
        """)
        for rec in capacity_check:
            if not rec['has_capacity']:
                print(f"   ❌ Zone {rec['zone_id']} is missing capacity property!")
            else:
                print(f"   ✅ Zone {rec['zone_id']} has capacity={rec['capacity']}")

    # 7. Check underutilization
    print("\n7. CHECKING FOR UNDERUTILIZATION...")
    underutil_result = session.run("""
        MATCH (z:Zone)<-[:OCCURRED_IN]-(sa:SpatialActivity)
        WHERE sa.timestamp >= datetime($start_time)
        AND sa.timestamp <= datetime($end_time)
        AND sa.hour IN [9, 10, 11, 14, 15, 16, 17]
        AND NOT sa.is_weekend
        WITH z,
             avg(sa.occupancy) as avg_occupancy,
             max(sa.occupancy) as max_occupancy,
             count(sa) as data_points
        WHERE avg_occupancy < (z.capacity * 0.2)
        AND data_points > 5
        RETURN z.zone_id as zone_id,
               z.name as zone_name,
               z.capacity as capacity,
               avg_occupancy,
               max_occupancy,
               data_points
        ORDER BY avg_occupancy ASC
    """, {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat()
    })

    underutil_records = list(underutil_result)
    if len(underutil_records) > 0:
        print(f"   ✅ Found {len(underutil_records)} underutilized zones")
        for rec in underutil_records:
            util_rate = (rec['avg_occupancy'] / rec['capacity']) * 100
            print(f"   - {rec['zone_id']}: {util_rate:.1f}% utilization")
    else:
        print("   ❌ No underutilization detected")

print("\n" + "=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)

driver.close()
