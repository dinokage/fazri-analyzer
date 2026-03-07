#!/usr/bin/env python3
"""
Test script to verify eSSL connector works with simulator data.

This script tests the connector against the simulated MySQL database
and verifies that data can be fetched and normalized correctly.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path to import connector
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from services.data_pipeline.connector_base import ConnectorConfig, ConnectorType, ConnectionMethod
from services.data_pipeline.connectors.essl_connector import ESSLCardReaderConnector


async def test_essl_connector():
    """Test the eSSL connector with simulator."""
    print("=" * 60)
    print("eSSL Connector Test")
    print("=" * 60)

    # Create connector configuration
    config = ConnectorConfig(
        connector_id="essl_simulator_test",
        institution_id="test_university",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        credentials={
            'host': 'localhost',
            'port': 3307,
            'username': 'root',
            'password': 'essl_password',
            'database': 'essl_db',
            'table_name': 'AccessLogs'
        },
        field_mapping={
            'UserID': 'entity_id',
            'CardNo': 'card_id',
            'AccessTime': 'timestamp',
            'DoorID': 'location_id',
            'EventType': 'event_type'
        }
    )

    print(f"\nConnector Configuration:")
    print(f"  ID: {config.connector_id}")
    print(f"  Type: {config.connector_type}")
    print(f"  Host: {config.credentials['host']}:{config.credentials['port']}")
    print(f"  Database: {config.credentials['database']}")

    # Create connector instance
    connector = ESSLCardReaderConnector(config)

    # Test 1: Connection test
    print("\n" + "=" * 60)
    print("Test 1: Connection Test")
    print("=" * 60)

    try:
        is_connected = await connector.test_connection()
        if is_connected:
            print("✓ Connection successful!")
        else:
            print("✗ Connection failed")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

    # Test 2: Get sample data
    print("\n" + "=" * 60)
    print("Test 2: Sample Data Retrieval")
    print("=" * 60)

    try:
        sample_data = await connector.get_sample_data(n_records=5)
        print(f"✓ Retrieved {len(sample_data)} sample records")

        if sample_data:
            print("\nSample record (raw):")
            for key, value in sample_data[0].items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"✗ Sample data error: {e}")
        return False

    # Test 3: Normalize data
    print("\n" + "=" * 60)
    print("Test 3: Data Normalization")
    print("=" * 60)

    try:
        normalized_data = connector.normalize_data(sample_data)
        print(f"✓ Normalized {len(normalized_data)} records")

        if normalized_data:
            print("\nNormalized record:")
            for key, value in normalized_data[0].items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"✗ Normalization error: {e}")
        return False

    # Test 4: Fetch recent data (last 24 hours)
    print("\n" + "=" * 60)
    print("Test 4: Recent Data Fetch (Last 24 Hours)")
    print("=" * 60)

    try:
        since = datetime.now() - timedelta(days=1)
        recent_data = await connector.fetch_data(since)
        print(f"✓ Fetched {len(recent_data)} events from last 24 hours")

        if recent_data:
            # Show event distribution
            event_types = {}
            for event in recent_data:
                event_type = event.get('EventType', 'UNKNOWN')
                event_types[event_type] = event_types.get(event_type, 0) + 1

            print("\nEvent type distribution:")
            for event_type, count in event_types.items():
                print(f"  {event_type}: {count}")

            # Show door distribution
            doors = {}
            for event in recent_data:
                door = event.get('DoorID', 'UNKNOWN')
                doors[door] = doors.get(door, 0) + 1

            print("\nDoor usage:")
            for door, count in sorted(doors.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {door}: {count}")
    except Exception as e:
        print(f"✗ Data fetch error: {e}")
        return False

    # Test 5: Fetch older data (7 days ago)
    print("\n" + "=" * 60)
    print("Test 5: Historical Data Fetch (7 Days Ago)")
    print("=" * 60)

    try:
        since = datetime.now() - timedelta(days=7)
        historical_data = await connector.fetch_data(since)
        print(f"✓ Fetched {len(historical_data)} events from last 7 days")

        # Show daily distribution
        if historical_data:
            daily_counts = {}
            for event in historical_data:
                timestamp = event.get('AccessTime')
                if isinstance(timestamp, datetime):
                    date_str = timestamp.date().isoformat()
                    daily_counts[date_str] = daily_counts.get(date_str, 0) + 1

            print("\nDaily event counts:")
            for date, count in sorted(daily_counts.items())[-7:]:
                print(f"  {date}: {count}")
    except Exception as e:
        print(f"✗ Historical data error: {e}")
        return False

    # Cleanup
    await connector.close()

    print("\n" + "=" * 60)
    print("All Tests Passed! ✓")
    print("=" * 60)
    print("\nThe eSSL connector is working correctly with the simulator.")
    print("You can now integrate it with the data pipeline!")

    return True


async def main():
    """Main test execution."""
    success = await test_essl_connector()

    if not success:
        print("\n" + "=" * 60)
        print("Tests Failed ✗")
        print("=" * 60)
        print("\nMake sure:")
        print("1. MySQL simulator is running:")
        print("   docker-compose -f docker-compose.simulators.yml up -d essl-mysql")
        print("2. Data has been generated:")
        print("   docker-compose -f docker-compose.simulators.yml run --rm essl-data-generator")
        print("3. Port 3307 is accessible")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
