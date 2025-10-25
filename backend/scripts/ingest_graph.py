# backend/scripts/ingest_graph.py
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.entity_resolver import EntityResolver
from services.graph_builder import CampusGraphBuilder
from config import settings
import pandas as pd

# backend/scripts/ingest_graph.py - SIMPLIFIED VERSION

def main():
    """Main ingestion script"""
    print("🚀 Starting Neo4j Graph Ingestion")
    print("="*60)
    
    # Initialize
    data_dir = Path(__file__).parent.parent / "augmented"
    
    # Step 1: Build entity graph from resolver
    print("\n📊 Step 1: Building Entity Resolver")
    resolver = EntityResolver(data_dir)
    resolver.build_entity_graph()
    
    # Step 2: Initialize Neo4j
    print("\n📊 Step 2: Connecting to Neo4j")
    graph = CampusGraphBuilder(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    
    # Step 3: Clear and create indexes
    print("\n📊 Step 3: Preparing Database")
    response = input("⚠️  Clear existing database? (yes/no): ")
    if response.lower() == 'yes':
        graph.clear_database()
    graph.create_indexes()
    
    # Step 4: Build entity nodes (includes all profile data)
    print("\n📊 Step 4: Creating Entity Nodes from Profiles")
    graph.build_from_resolver(resolver)
    
    # Step 5: Enrich with role (if not already in entity_type)
    print("\n📊 Step 5: Enriching Profile Metadata")
    profiles_df = pd.read_csv(data_dir / "student_staff_profiles.csv")
    graph.create_profile_metadata(profiles_df)
    
    # Step 6: Ingest events
    print("\n📊 Step 6: Ingesting Events")
    
    # Load all datasets
    swipes_df = pd.read_csv(data_dir / "campus_card_swipes_augmented.csv")
    wifi_df = pd.read_csv(data_dir / "wifi_associations_logs_augmented.csv")
    library_df = pd.read_csv(data_dir / "library_checkouts_augmented.csv")
    bookings_df = pd.read_csv(data_dir / "lab_bookings_augmented.csv")
    cctv_df = pd.read_csv(data_dir / "cctv_frames_augmented.csv")
    helpdesk_df = pd.read_csv(data_dir / "helpdesk_augmented.csv")
    
    # How many events to ingest?
    event_limit = 40000
    print(f"\n⚙️  Ingesting up to {event_limit} events from each dataset...")
    
    print("\n1️⃣  Ingesting card swipes...")
    graph.ingest_swipe_events(swipes_df.head(event_limit))
    
    print("\n2️⃣  Ingesting Wi-Fi connections...")
    graph.ingest_wifi_events(wifi_df.head(event_limit))
    
    print("\n3️⃣  Ingesting library checkouts...")
    graph.ingest_library_events(library_df.head(event_limit))
    
    print("\n4️⃣  Ingesting room bookings...")
    graph.ingest_booking_events(bookings_df.head(event_limit))
    
    print("\n5️⃣  Ingesting CCTV sightings...")
    graph.ingest_cctv_events(cctv_df.head(event_limit))
    
    print("\n6️⃣  Ingesting helpdesk tickets...")
    graph.ingest_helpdesk_events(helpdesk_df.head(event_limit))
    
    print("\n" + "="*60)
    print("✅ Ingestion Complete!")
    print("="*60)
    
    # Get final statistics
    print("\n📊 Final Graph Statistics:")
    stats_query = """
    MATCH (e:Entity) WITH count(e) as entities
    MATCH (ev:Event) WITH entities, count(ev) as events
    MATCH (l:Location) WITH entities, events, count(l) as locations
    MATCH ()-[r]->() 
    RETURN entities, events, locations, count(r) as relationships
    """
    
    try:
        with graph.driver.session() as session:
            result = session.run(stats_query)
            record = result.single()
            
            print(f"  👥 Entities: {record['entities']:,}")
            print(f"  📅 Events: {record['events']:,}")
            print(f"  📍 Locations: {record['locations']:,}")
            print(f"  🔗 Relationships: {record['relationships']:,}")
    except Exception as e:
        print(f"  ⚠️  Could not fetch stats: {e}")
    
    # Event type breakdown
    print("\n📊 Event Type Breakdown:")
    event_type_query = """
    MATCH (ev:Event)
    RETURN ev.event_type as type, count(ev) as count
    ORDER BY count DESC
    """
    
    try:
        with graph.driver.session() as session:
            result = session.run(event_type_query)
            for record in result:
                print(f"  📌 {record['type']}: {record['count']:,}")
    except Exception as e:
        print(f"  ⚠️  Could not fetch event breakdown: {e}")
    
    print("\n" + "="*60)
    print("🎉 Visit http://localhost:7474 to explore the graph!")
    print("\n📝 Example Cypher Queries:")
    print("="*60)
    print("\n1️⃣  View entity with all events:")
    print("   MATCH (e:Entity {entity_id: 'E100001'})-[:PERFORMED]->(ev:Event)")
    print("   OPTIONAL MATCH (ev)-[:AT_LOCATION]->(l:Location)")
    print("   RETURN e, ev, l")
    
    print("\n2️⃣  Find entities at a location:")
    print("   MATCH (e:Entity)-[:PERFORMED]->(ev:Event)-[:AT_LOCATION]->(l:Location {location_id: 'L101'})")
    print("   RETURN e.name, ev.timestamp, ev.event_type")
    print("   ORDER BY ev.timestamp DESC")
    print("   LIMIT 20")
    
    print("\n3️⃣  View CCTV sightings:")
    print("   MATCH (e:Entity)-[:PERFORMED]->(ev:Event {event_type: 'cctv_sighting'})")
    print("   RETURN e.name, ev.timestamp, ev.location")
    print("   LIMIT 50")
    
    print("\n4️⃣  Find linked entities (duplicates):")
    print("   MATCH (e1:Entity)-[:SAME_AS]-(e2:Entity)")
    print("   RETURN e1.entity_id, e1.name, e2.entity_id, e2.name")
    print("   LIMIT 20")
    
    print("\n5️⃣  Entity timeline:")
    print("   MATCH (e:Entity {name: 'John Smith'})-[:PERFORMED]->(ev:Event)")
    print("   RETURN ev.event_type, ev.timestamp, ev.location")
    print("   ORDER BY ev.timestamp")
    
    graph.close()
    print("\n✅ Neo4j connection closed")

if __name__ == "__main__":
    main()