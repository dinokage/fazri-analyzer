# backend/scripts/test_fusion.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests

BASE_URL = "http://localhost:8000"

def test_fusion_report():
    """Test the fusion report endpoint"""
    
    # Get a sample entity
    response = requests.get(f"{BASE_URL}/api/v1/entities/?limit=1")
    entities = response.json()['entities']
    
    if not entities:
        print("No entities found")
        return
    
    entity_id = entities[0]['entity_id']
    print(f"\n📊 Testing Fusion Report for Entity: {entity_id}")
    print("="*60)
    
    # Get fusion report
    response = requests.get(f"{BASE_URL}/api/v1/entities/{entity_id}/fusion-report")
    report = response.json()
    
    print(f"\n🎯 Entity: {report['name']} ({report['entity_id']})")
    print(f"   Overall Confidence: {report['overall_confidence']}")
    
    print(f"\n📋 Identifiers by Source:")
    for source, identifiers in report['identifiers_by_source'].items():
        print(f"\n   {source.upper()}:")
        for id_info in identifiers:
            print(f"      - {id_info['type']}: {id_info['value']} (confidence: {id_info['confidence']})")
    
    print(f"\n🔗 Linked Entities:")
    for linked in report['linked_entities'][:5]:  # Top 5
        print(f"   - {linked['name']} ({linked['entity_id']})")
        print(f"     Confidence: {linked['confidence']}")
        print(f"     Shared: {', '.join(linked['shared_identifiers'])}")
    
    print(f"\n📊 Fusion Summary:")
    summary = report['fusion_summary']
    print(f"   Total Sources: {summary['total_sources']}")
    print(f"   Total Identifiers: {summary['total_identifiers']}")
    print(f"   Identifier Types: {', '.join(summary['identifier_types'])}")
    print(f"   Most Reliable Source: {summary['most_reliable_source']}")

if __name__ == "__main__":
    test_fusion_report()