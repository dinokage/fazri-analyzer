# backend/scripts/check_data_status.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.graph_builder import get_graph_builder

def check_data():
    """Check what data we have"""
    
    print("\n" + "="*60)
    print("🔍 Checking Database Contents")
    print("="*60)
    
    graph = get_graph_builder()
    
    # Check total counts
    queries = {
        'Entities': "MATCH (e:Entity) RETURN count(e) as count",
        'Events': "MATCH (ev:Event) RETURN count(ev) as count",
        'Locations': "MATCH (l:Location) RETURN count(l) as count"
    }
    
    for name, query in queries.items():
        with graph.driver.session() as session:
            result = session.run(query)
            count = result.single()['count']
            print(f"   {name}: {count}")
    
    # Check entities with events
    print(f"\n📊 Entities with Events:")
    query = """
    MATCH (e:Entity)-[:PERFORMED]->(ev:Event)
    WITH e, count(ev) as event_count
    RETURN e.entity_id as entity_id, 
           e.name as name, 
           event_count
    ORDER BY event_count DESC
    LIMIT 100
    """
    
    with graph.driver.session() as session:
        result = session.run(query)
        records = list(result)
        
        if records:
            for record in records:
                print(f"   {record['entity_id']}: {record['name']} - {record['event_count']} events")
        else:
            print("   ❌ No entities have any events!")
            print("\n💡 This means events weren't linked to entities properly.")
            print("   Let's check what's in the Events table...")
    
    # Check sample events
    print(f"\n📋 Sample Events:")
    query = """
    MATCH (ev:Event)
    RETURN ev.event_id as event_id,
           ev.event_type as event_type,
           ev.timestamp as timestamp
    LIMIT 5
    """
    
    with graph.driver.session() as session:
        result = session.run(query)
        for record in result:
            print(f"   {record['event_id']}: {record['event_type']} at {record['timestamp']}")
    
    # Check if events are orphaned (not linked to entities)
    print(f"\n🔗 Checking Event Links:")
    query = """
    MATCH (ev:Event)
    OPTIONAL MATCH (e:Entity)-[:PERFORMED]->(ev)
    RETURN count(ev) as total_events,
           count(e) as linked_events,
           count(ev) - count(e) as orphaned_events
    """
    
    with graph.driver.session() as session:
        result = session.run(query)
        record = result.single()
        print(f"   Total Events: {record['total_events']}")
        print(f"   Linked to Entities: {record['linked_events']}")
        print(f"   Orphaned (not linked): {record['orphaned_events']}")
    
    graph.close()
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    check_data()