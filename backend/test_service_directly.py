#!/usr/bin/env python3
"""Test anomaly detection service directly to see where it fails"""

import sys
import logging
from datetime import datetime
from services.anomaly_detection import AnomalyDetectionService

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 80)
print("TESTING ANOMALY DETECTION SERVICE DIRECTLY")
print("=" * 80)

NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Pressword@69"

try:
    print("\n1. Initializing service...")
    service = AnomalyDetectionService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    print("✓ Service initialized")

    print("\n2. Getting dataset time range...")
    dataset_info = service.get_dataset_time_range()
    print(f"✓ Dataset info: {dataset_info}")

    print("\n3. Detecting anomalies (entire dataset)...")
    anomalies = service.detect_all_anomalies()
    print(f"✓ Found {len(anomalies)} anomalies")

    if len(anomalies) > 0:
        print("\n4. Sample anomalies:")
        for i, anomaly in enumerate(anomalies[:5]):
            print(f"\n   Anomaly {i+1}:")
            print(f"   - Type: {anomaly.get('type')}")
            print(f"   - Severity: {anomaly.get('severity')}")
            print(f"   - Location: {anomaly.get('location')}")
            print(f"   - Description: {anomaly.get('description', 'N/A')[:100]}")
    else:
        print("\n❌ ZERO ANOMALIES RETURNED!")
        print("   Checking individual detection methods...")

        # Try each method separately
        print("\n   Testing _detect_overcrowding_simplified...")
        try:
            start = datetime(2025, 8, 1)
            end = datetime(2025, 11, 1)
            overcrowding = service._detect_overcrowding_simplified(start, end)
            print(f"   ✓ Overcrowding: {len(overcrowding)} anomalies")
            if overcrowding:
                print(f"      First: {overcrowding[0]}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

        print("\n   Testing _detect_underutilization_simplified...")
        try:
            underutil = service._detect_underutilization_simplified(start, end)
            print(f"   ✓ Underutilization: {len(underutil)} anomalies")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

        print("\n   Testing _detect_data_integrity_anomalies_simplified...")
        try:
            integrity = service._detect_data_integrity_anomalies_simplified(start, end)
            print(f"   ✓ Data integrity: {len(integrity)} anomalies")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

except Exception as e:
    print(f"\n❌ FATAL ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
