# backend/scripts/test_predictor.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_predictor():
    """Test ML-based location prediction"""
    
    print("\n" + "="*60)
    print("🎯 Testing ML-Based Location Predictor")
    print("="*60)
    
    # Get entity with activity
    # response = requests.get(f"{BASE_URL}/api/v1/entities/?limit=300")
    # entities = response.json()['entities']
    entities = ['E102479', 'E103820', 'E105386', 'E100128', 'E101772']
    
    entity_id = None
    for entity in entities:
        resp = requests.get(f"{BASE_URL}/api/v1/graph/timeline/{entity}")
        if resp.status_code == 200 and resp.json()['total_events'] > 10:
            entity_id = entity
            entity_name = 'chomu'
            break
    
    if not entity_id:
        print("❌ No suitable entity found (need 10+ events)")
        return
    
    print(f"\n📊 Testing with Entity: {entity_name} ({entity_id})")
    
    # Test 1: Current time prediction
    print(f"\n1️⃣  Current Location Prediction")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/graph/predict/location/{entity_id}"
        )
        response.raise_for_status()
        prediction = response.json()
        
        print(f"   Method: {prediction.get('method')}")
        
        for i, pred in enumerate(prediction.get('predictions', []), 1):
            print(f"\n   Prediction {i}:")
            print(f"      Location: {pred['location']}")
            print(f"      Confidence: {pred['confidence']:.1%}")
            
            explanation = pred.get('explanation', {})
            print(f"      Confidence Level: {explanation.get('confidence_level', 'N/A')}")
            print(f"      Reasoning: {explanation.get('reasoning', 'N/A')}")
            
            if explanation.get('evidence'):
                print(f"      Evidence:")
                for evidence in explanation['evidence']:
                    print(f"         - {evidence}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Gap prediction
    print(f"\n2️⃣  Gap Prediction")
    print("-" * 60)
    
    try:
        # Get timeline with gaps
        response = requests.get(
            f"{BASE_URL}/api/v1/graph/timeline/{entity_id}/with-gaps"
        )
        timeline = response.json()
        
        gaps = timeline.get('gaps', [])
        
        if gaps:
            # Use first significant gap
            gap = gaps[0]
            print(f"   Found gap: {gap['duration_hours']:.1f} hours")
            print(f"   From: {gap['last_location']} → {gap['next_location']}")
            
            # Predict during gap
            response = requests.post(
                f"{BASE_URL}/api/v1/graph/predict/gap/{entity_id}",
                json={
                    'gap_start': gap['start_time'],
                    'gap_end': gap['end_time']
                }
            )
            response.raise_for_status()
            gap_predictions = response.json()
            
            print(f"\n   Predictions during gap:")
            for pred in gap_predictions.get('predictions', []):
                time_str = pred['time'][:19]
                print(f"      {time_str}: {pred['location']} ({pred['confidence']:.1%})")
                print(f"         {pred['explanation']['reasoning']}")
        else:
            print("   No gaps found to predict")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ Testing Complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    test_predictor()