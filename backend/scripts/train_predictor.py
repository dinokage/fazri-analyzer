# backend/scripts/train_predictor.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.graph_builder import get_graph_builder
from services.ml_predictor import LocationPredictor
from datetime import datetime, timedelta

def train_predictors():
    """Train location predictors for all entities with sufficient data"""
    
    print("\n" + "="*60)
    print("🎓 Training Location Predictors")
    print("="*60)
    
    graph = get_graph_builder()
    
    # Get entities with sufficient activity
    query = """
    MATCH (e:Entity)-[:PERFORMED]->(ev:Event)
    WITH e, count(ev) as event_count
    WHERE event_count >= 10
    RETURN e.entity_id as entity_id, e.name as name, event_count
    ORDER BY event_count DESC
    LIMIT 20
    """
    
    with graph.driver.session() as session:
        result = session.run(query)
        entities = [dict(record) for record in result]
    
    print(f"\nFound {len(entities)} entities with sufficient data for training")
    
    models_dir = Path(__file__).parent.parent / 'models'
    models_dir.mkdir(exist_ok=True)
    
    trained_count = 0
    
    for entity in entities:
        entity_id = entity['entity_id']
        name = entity['name']
        event_count = entity['event_count']
        
        print(f"\n📊 Training predictor for {name} ({entity_id})")
        print(f"   Events available: {event_count}")
        
        # Get all events for this entity
        events = graph.get_entity_timeline(entity_id)
        
        # Train predictor
        predictor = LocationPredictor()
        result = predictor.train(events)
        
        if result['success']:
            print(f"   ✅ Training successful!")
            print(f"      Training samples: {result['training_samples']}")
            print(f"      Unique locations: {result['unique_locations']}")
            
            # Print feature importance
            print(f"      Feature importance:")
            for feature, importance in sorted(
                result['feature_importance'].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                print(f"         {feature}: {importance:.3f}")
            
            # Save model
            model_path = models_dir / f"predictor_{entity_id}.pkl"
            predictor.save_model(model_path)
            print(f"      💾 Model saved to {model_path}")
            
            trained_count += 1
        else:
            print(f"   ❌ Training failed: {result['message']}")
    
    print(f"\n{'='*60}")
    print(f"✅ Training Complete!")
    print(f"   Trained {trained_count}/{len(entities)} models")
    print(f"{'='*60}\n")
    
    graph.close()

if __name__ == "__main__":
    train_predictors()