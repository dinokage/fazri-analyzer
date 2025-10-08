# backend/scripts/test_timeline.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_timeline_features():
    """Test all timeline endpoints"""
    
    print(f"\n{'='*60}")
    print(f"🔍 Finding Entity with Activity...")
    print(f"{'='*60}")
    
    # Get entities
    try:
        response = requests.get(f"{BASE_URL}/api/v1/entities/?limit=10")
        response.raise_for_status()
        entities = response.json()['entities']
    except Exception as e:
        print(f"❌ Error fetching entities: {e}")
        return
    
    # Find entity with events
    entity_id = None
    for entity in entities:
        try:
            # Try to get basic timeline first
            resp = requests.get(f"{BASE_URL}/api/v1/graph/timeline/{entity['entity_id']}")
            if resp.status_code == 200:
                timeline_data = resp.json()
                if timeline_data.get('total_events', 0) > 0:
                    entity_id = entity['entity_id']
                    print(f"✅ Found entity with activity: {entity_id}")
                    break
        except Exception as e:
            continue
    
    if not entity_id:
        print("❌ No entities with activity found")
        print("💡 Tip: Make sure you've run the ingestion script first:")
        print("   python scripts/ingest_graph.py")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 Testing Timeline Features for Entity: {entity_id}")
    print(f"{'='*60}")
    
    # Test 1: Basic Timeline
    print(f"\n1️⃣  Basic Timeline")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/graph/timeline/{entity_id}")
        response.raise_for_status()
        basic_timeline = response.json()
        
        print(f"   Total Events: {basic_timeline.get('total_events', 0)}")
        print(f"   Events retrieved: {len(basic_timeline.get('events', []))}")
        
        if basic_timeline.get('events'):
            print(f"\n   Sample Events:")
            for event in basic_timeline['events'][:3]:
                print(f"      - {event.get('event_type')} at {event.get('location')} ({event.get('timestamp', '')[:19]})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 2: Timeline with gaps
    print(f"\n2️⃣  Timeline with Gap Detection")
    print("-" * 60)
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/graph/timeline/{entity_id}/with-gaps",
            params={'gap_threshold_hours': 2}
        )
        response.raise_for_status()
        timeline_data = response.json()
        
        print(f"   Total Events: {timeline_data.get('total_events', 0)}")
        
        if timeline_data.get('start_date'):
            print(f"   Date Range: {timeline_data['start_date'][:10]} to {timeline_data['end_date'][:10]}")
        
        stats = timeline_data.get('statistics', {})
        if stats:
            print(f"\n   📊 Statistics:")
            print(f"      - Most Visited: {stats.get('most_visited_location', 'N/A')}")
            if stats.get('event_type_distribution'):
                print(f"      - Event Types: {', '.join(stats['event_type_distribution'].keys())}")
            print(f"      - Avg Events/Day: {stats.get('avg_events_per_day', 0):.1f}")
        
        gaps = timeline_data.get('gaps', [])
        if gaps:
            print(f"\n   ⏰ Detected {len(gaps)} gap(s):")
            for i, gap in enumerate(gaps[:3], 1):
                print(f"      Gap {i}: {gap.get('duration_hours', 0):.1f} hours")
                print(f"         From: {gap.get('last_location')} → {gap.get('next_location')}")
        else:
            print(f"\n   ✅ No significant gaps detected")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Human-readable summary
    print(f"\n3️⃣  Human-Readable Summary")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/graph/timeline/{entity_id}/summary")
        response.raise_for_status()
        summary = response.json()
        
        print(f"\n   📝 Summary:")
        summary_text = summary.get('summary', 'No summary available')
        # Wrap long lines
        import textwrap
        wrapped = textwrap.fill(summary_text, width=70, initial_indent='      ', subsequent_indent='      ')
        print(wrapped)
        
        detailed = summary.get('detailed_summary', {})
        if detailed:
            print(f"\n   📋 Detailed Breakdown:")
            for period, details in detailed.items():
                desc = details.get('description', '')
                wrapped = textwrap.fill(desc, width=65, initial_indent='      ', subsequent_indent='         ')
                print(f"      {period.capitalize()}:")
                print(wrapped)
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Activity heatmap
    print(f"\n4️⃣  Activity Heatmap (Last 7 Days)")
    print("-" * 60)
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/graph/timeline/{entity_id}/heatmap",
            params={'days': 7}
        )
        response.raise_for_status()
        heatmap = response.json()
        
        heatmap_data = heatmap.get('heatmap', [])
        if heatmap_data:
            print(f"   Total data points: {len(heatmap_data)}")
            
            # Show busiest hours
            from collections import Counter
            hour_counts = Counter([h['hour'] for h in heatmap_data])
            top_hours = hour_counts.most_common(3)
            
            print(f"\n   🔥 Busiest Hours:")
            for hour, count in top_hours:
                print(f"      {hour:02d}:00 - {count} events")
        else:
            print(f"   No heatmap data available")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Pattern detection
    print(f"\n5️⃣  Pattern Detection")
    print("-" * 60)
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/graph/timeline/{entity_id}/patterns",
            params={'days': 7}
        )
        response.raise_for_status()
        patterns = response.json()
        
        pattern_info = patterns.get('patterns', {})
        if pattern_info.get('has_routine'):
            print(f"   ✅ Routine detected!")
            print(f"   Routine Strength: {pattern_info.get('routine_strength', 0):.1%}")
            
            typical_hours = pattern_info.get('typical_hours', {})
            if typical_hours:
                print(f"\n   📅 Typical Schedule:")
                for hour in sorted([int(h) for h in typical_hours.keys()])[:5]:
                    hour_data = typical_hours[str(hour)]
                    print(f"      {hour:02d}:00 - {hour_data['location']} ({hour_data['confidence']:.0%} confidence)")
            
            sequences = pattern_info.get('common_sequences', [])
            if sequences:
                print(f"\n   🔄 Common Movement Patterns:")
                for seq in sequences[:3]:
                    print(f"      {seq['sequence']} ({seq['count']} times)")
        else:
            print(f"   No clear routine detected (insufficient data or irregular schedule)")
        
        prediction = patterns.get('next_location_prediction', {})
        if prediction.get('predicted_location'):
            print(f"\n   🎯 Next Location Prediction:")
            print(f"      Location: {prediction['predicted_location']}")
            print(f"      Confidence: {prediction['confidence']:.0%}")
            print(f"      Evidence: {prediction['evidence']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ Testing Complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    test_timeline_features()