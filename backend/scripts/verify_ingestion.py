# backend/scripts/verify_ingestion.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from services.graph_builder import get_graph_builder

def verify_ingestion():
    """Verify that events are being linked to entities properly"""
    
    print("\n" + "="*60)
    print("🔍 Verifying Ingestion")
    print("="*60)
    
    data_dir = Path(__file__).parent.parent / "datasets"
    graph = get_graph_builder()
    
    # Load profiles
    profiles_df = pd.read_csv(data_dir / "student_staff_profiles.csv")
    print(f"\n📊 Profiles: {len(profiles_df)} rows")
    print(f"   Sample entity_ids: {profiles_df['entity_id'].head(3).tolist()}")
    
    # Load swipes
    swipes_df = pd.read_csv(data_dir / "campus_card_swipes.csv")
    print(f"\n📊 Swipes: {len(swipes_df)} rows")
    print(f"   Sample card_ids: {swipes_df['card_id'].head(3).tolist()}")
    
    # Check if card_ids from swipes exist in profiles
    sample_card_id = str(swipes_df['card_id'].iloc[0])
    print(f"\n🔍 Checking if card_id '{sample_card_id}' exists in profiles...")
    
    if sample_card_id in profiles_df['card_id'].astype(str).values:
        print(f"   ✅ Found in profiles!")
        entity_id = profiles_df[profiles_df['card_id'].astype(str) == sample_card_id]['entity_id'].iloc[0]
        print(f"   Belongs to entity: {entity_id}")
        
        # Check if this entity exists in Neo4j
        query = """
        MATCH (e:Entity {card_id: $card_id})
        RETURN e.entity_id as entity_id, e.name as name
        """
        
        with graph.driver.session() as session:
            result = session.run(query, card_id=sample_card_id)
            record = result.single()
            
            if record:
                print(f"   ✅ Entity exists in Neo4j: {record['entity_id']} ({record['name']})")
                
                # Check if this entity has events
                query2 = """
                MATCH (e:Entity {card_id: $card_id})-[:PERFORMED]->(ev:Event)
                RETURN count(ev) as event_count
                """
                
                result2 = session.run(query2, card_id=sample_card_id)
                count = result2.single()['event_count']
                print(f"   Events for this entity: {count}")
                
                if count == 0:
                    print(f"   ❌ Entity exists but has NO events!")
                    print(f"   This means the event ingestion isn't linking properly.")
            else:
                print(f"   ❌ Entity NOT found in Neo4j!")
    else:
        print(f"   ❌ card_id not found in profiles!")
    
    graph.close()

if __name__ == "__main__":
    verify_ingestion()