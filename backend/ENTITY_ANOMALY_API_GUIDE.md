# Entity Anomaly Detection API Guide

## Overview

The entity anomaly endpoint allows you to query all anomalies for a specific student, faculty, or staff member by their entity ID.

## Endpoint

```
GET /api/v1/anomalies/by-entity/{entity_id}
```

## Parameters

- `entity_id` (path parameter, required): The unique entity ID (e.g., E100295, E100298)
- `start_date` (query parameter, optional): Start date in YYYY-MM-DD format
- `end_date` (query parameter, optional): End date in YYYY-MM-DD format

If no date range is provided, it searches the entire dataset.

## Response Format

```json
{
  "success": true,
  "data": {
    "entity": {
      "entity_id": "E100295",
      "name": "Ishaan Kumar",
      "role": "student",
      "department": "EEE",
      "card_id": "CARD_295"
    },
    "anomalies": [
      {
        "id": "off_hours_E100295_LAB_101_2025-09-15T02:30:00",
        "type": "off_hours_access",
        "severity": "critical",
        "entity_id": "E100295",
        "entity_name": "Ishaan Kumar",
        "entity_role": "student",
        "location": "LAB_101",
        "location_name": "Computer Science Lab 101",
        "timestamp": "2025-09-15T02:30:00",
        "description": "Ishaan Kumar (student) accessed Computer Science Lab 101 at 2:00 (outside operating hours 7:00-21:00)",
        "details": {...}
      }
    ],
    "total_count": 15,
    "time_range": "Entire dataset",
    "detection_time": "2025-10-25T12:45:00"
  }
}
```

## Types of Entity Anomalies Detected

1. **Off-Hours Access** (critical/high)
   - Accessing labs/facilities outside operating hours
   - Example: Accessing LAB_101 at 2 AM (hours: 7 AM - 9 PM)

2. **Role Violations** (critical)
   - Students accessing faculty-only rooms (ROOM_A1, ROOM_A2)
   - Unauthorized access based on role

3. **Department Violations** (high)
   - Non-ECE students accessing ECE-restricted LAB_305
   - Department-based access restrictions

4. **Impossible Travel** (critical)
   - Same person in 2 different locations < 2 minutes apart
   - Potential card sharing or system glitch

5. **Location Mismatches** (high)
   - Card swipe location ≠ WiFi connection location
   - Indicates tailgating or fraudulent access

6. **Curfew Violations** (high)
   - Students entering hostel after 11 PM curfew

7. **Excessive Access** (medium)
   - Unusually high frequency of access (> 50 swipes/day)

8. **Booking No-Shows** (medium)
   - Room/lab booked but no actual access recorded

## Usage Examples

### 1. Get all anomalies for a specific student

```bash
curl "http://localhost:8000/api/v1/anomalies/by-entity/E100295" | python3 -m json.tool
```

### 2. Get anomalies for a date range

```bash
curl "http://localhost:8000/api/v1/anomalies/by-entity/E100295?start_date=2025-09-01&end_date=2025-09-30" | python3 -m json.tool
```

### 3. Get only critical/high severity anomalies for entity

```bash
# Get all anomalies
curl "http://localhost:8000/api/v1/anomalies/by-entity/E100295" | \
  python3 -c "import sys, json; data=json.load(sys.stdin); \
  critical = [a for a in data['data']['anomalies'] if a['severity'] in ['critical', 'high']]; \
  print(f\"Critical/High anomalies: {len(critical)}\"); \
  print(json.dumps(critical[:5], indent=2))"
```

### 4. Check if entity exists before querying

```bash
# This returns 404 if entity doesn't exist
curl "http://localhost:8000/api/v1/anomalies/by-entity/INVALID_ID"
```

## Sample Entity IDs (From Your Database)

- `E100294` - Divya Rao (Faculty, BIO)
- `E100295` - Ishaan Kumar (Student, EEE)
- `E100296` - Ananya Kumar (Student, CIVIL)
- `E100297` - Divya Mehta (Student, Admin)
- `E100298` - Ishaan Sharma (Student, ECE)

## Integration with Other Endpoints

You can combine entity-level anomalies with other endpoints:

```bash
# 1. Get entity profile and anomalies
curl "http://localhost:8000/api/v1/anomalies/by-entity/E100295"

# 2. Get overall summary for context
curl "http://localhost:8000/api/v1/anomalies/summary"

# 3. Get location-specific anomalies
curl "http://localhost:8000/api/v1/anomalies/by-location/LAB_101"

# 4. Get all critical severity anomalies (includes entity-level)
curl "http://localhost:8000/api/v1/anomalies/by-severity/critical"
```

## Testing

Run the provided test script:

```bash
./test_entity_endpoint.sh
```

This will test:
- Valid entity queries
- Date range filtering
- Non-existent entity handling (404 error)

## Interactive API Documentation

Open in browser: **http://localhost:8000/docs**

Search for "by-entity" endpoint and use the interactive Swagger UI to test queries.

## Error Handling

### 404 - Entity Not Found
```json
{
  "detail": "Entity 'INVALID_ID' not found"
}
```

### 400 - Invalid Date Format
```json
{
  "detail": "Invalid date format. Use YYYY-MM-DD"
}
```

### 500 - Server Error
```json
{
  "detail": "Error retrieving entity anomalies: <error message>"
}
```

## Performance Notes

- Entity-level detection typically processes 100k+ records
- Response time: 1-3 seconds for entire dataset
- Date range filtering improves performance
- Results are sorted by timestamp (most recent first)

## Next Steps

1. **Restart your FastAPI server** to load the new endpoint
2. Test with sample entity IDs above
3. Check the interactive docs at `/docs`
4. Use in your frontend to display per-user anomaly reports
