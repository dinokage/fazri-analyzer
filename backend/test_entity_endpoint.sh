#!/bin/bash
# Test the new entity anomaly endpoint

echo "=============================================================================="
echo "TESTING ENTITY ANOMALY ENDPOINT"
echo "=============================================================================="

# Example 1: Get all anomalies for student E100295 (Ishaan Kumar)
echo ""
echo "1. Get all anomalies for entity E100295 (Student - Ishaan Kumar):"
echo "------------------------------------------------------------------------------"
curl -s "http://localhost:8000/api/v1/anomalies/by-entity/E100295" | python3 -m json.tool | head -60

# Example 2: Get anomalies for faculty E100294 (Divya Rao)
echo ""
echo ""
echo "2. Get all anomalies for entity E100294 (Faculty - Divya Rao):"
echo "------------------------------------------------------------------------------"
curl -s "http://localhost:8000/api/v1/anomalies/by-entity/E100294" | python3 -m json.tool | head -60

# Example 3: Get anomalies for entity E100298 with date range
echo ""
echo ""
echo "3. Get anomalies for E100298 (Student - Ishaan Sharma) from Sept to Oct 2025:"
echo "------------------------------------------------------------------------------"
curl -s "http://localhost:8000/api/v1/anomalies/by-entity/E100298?start_date=2025-09-01&end_date=2025-10-25" | python3 -m json.tool | head -60

# Example 4: Test with non-existent entity (should return 404)
echo ""
echo ""
echo "4. Test with non-existent entity (should return 404 error):"
echo "------------------------------------------------------------------------------"
curl -s "http://localhost:8000/api/v1/anomalies/by-entity/INVALID_ID" | python3 -m json.tool

echo ""
echo "=============================================================================="
echo "TEST COMPLETE"
echo "=============================================================================="
