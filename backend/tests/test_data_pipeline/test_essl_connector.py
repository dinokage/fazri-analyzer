# backend/tests/test_data_pipeline/test_essl_connector.py
import pytest
import json
from pathlib import Path
from datetime import datetime
from backend.services.data_pipeline.connectors.essl_connector import ESSLCardReaderConnector
from backend.services.data_pipeline.connector_base import ConnectorConfig, ConnectorType, ConnectionMethod


@pytest.fixture
def essl_config():
    """Create test configuration for eSSL connector."""
    return ConnectorConfig(
        connector_id="essl_test",
        institution_id="test_university",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        credentials={
            "host": "localhost",
            "port": 3306,
            "username": "test",
            "password": "test",
            "database": "essl_test",
            "table_name": "AccessLogs"
        },
        field_mapping={
            "UserID": "entity_id",
            "CardNo": "card_id",
            "AccessTime": "timestamp",
            "DoorID": "location_id"
        }
    )


@pytest.fixture
def sample_essl_data():
    """Load sample eSSL data from fixtures."""
    fixture_path = Path(__file__).parent / "fixtures" / "essl_sample_data.json"
    with open(fixture_path) as f:
        return json.load(f)


def test_essl_connector_creation(essl_config):
    """Test creating eSSL connector instance."""
    connector = ESSLCardReaderConnector(essl_config)
    assert connector.config.connector_id == "essl_test"
    assert connector.CONNECTOR_TYPE == ConnectorType.CARD_SWIPE


def test_essl_normalize_data(essl_config, sample_essl_data):
    """Test normalizing eSSL data to Fazri format."""
    connector = ESSLCardReaderConnector(essl_config)
    normalized = connector.normalize_data(sample_essl_data)

    assert len(normalized) == 2
    assert normalized[0]["entity_id"] == "E100001"
    assert normalized[0]["card_id"] == "1234567890"
    assert "timestamp" in normalized[0]
    assert "location_id" in normalized[0]


def test_essl_parse_timestamp(essl_config):
    """Test parsing various eSSL timestamp formats."""
    connector = ESSLCardReaderConnector(essl_config)

    # Test standard format
    ts1 = connector._parse_timestamp("2026-03-06 14:30:45")
    assert isinstance(ts1, datetime)
    assert ts1.year == 2026

    # Test alternate format
    ts2 = connector._parse_timestamp("06/03/2026 14:30:45")
    assert isinstance(ts2, datetime)
