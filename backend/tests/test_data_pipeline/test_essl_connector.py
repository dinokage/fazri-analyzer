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

    # Verify metadata fields are added
    assert normalized[0]["source_dataset"] == "essl_test"
    assert normalized[0]["source_connector"] == "essl_card_reader"
    assert normalized[0]["event_type"] == "card_swipe"


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
    assert ts2.year == 2026

    # Test ISO format
    ts3 = connector._parse_timestamp("2026-03-06T14:30:45")
    assert isinstance(ts3, datetime)
    assert ts3.year == 2026


def test_essl_invalid_timestamp_format(essl_config):
    """Test that invalid timestamp format raises ValueError."""
    connector = ESSLCardReaderConnector(essl_config)

    with pytest.raises(ValueError, match="Could not parse timestamp"):
        connector._parse_timestamp("invalid-timestamp")


def test_essl_validate_table_name_valid(essl_config):
    """Test that valid table names pass validation."""
    connector = ESSLCardReaderConnector(essl_config)

    # Valid names
    assert connector._validate_table_name("AccessLogs") == "AccessLogs"
    assert connector._validate_table_name("_private_table") == "_private_table"
    assert connector._validate_table_name("Table123") == "Table123"


def test_essl_validate_table_name_invalid(essl_config):
    """Test that invalid table names raise ValueError."""
    connector = ESSLCardReaderConnector(essl_config)

    # SQL injection attempts
    with pytest.raises(ValueError, match="Invalid table name"):
        connector._validate_table_name("Users; DROP TABLE Students--")

    with pytest.raises(ValueError, match="Invalid table name"):
        connector._validate_table_name("123_table")  # Starts with number

    with pytest.raises(ValueError, match="Invalid table name"):
        connector._validate_table_name("table-name")  # Contains hyphen


def test_essl_missing_database_credentials():
    """Test that missing database credentials raise ValueError."""
    config = ConnectorConfig(
        connector_id="essl_test",
        institution_id="test_university",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        credentials={"host": "localhost"}  # Missing username, password, database
    )

    with pytest.raises(ValueError, match="Missing required database credentials"):
        ESSLCardReaderConnector(config)


def test_essl_missing_api_credentials():
    """Test that missing API credentials raise ValueError."""
    config = ConnectorConfig(
        connector_id="essl_test",
        institution_id="test_university",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.REST_API,
        endpoint="https://api.example.com",
        credentials={}  # Missing api_key
    )

    with pytest.raises(ValueError, match="Missing required API credential"):
        ESSLCardReaderConnector(config)


def test_essl_get_sample_data_invalid_n_records(essl_config):
    """Test that invalid n_records parameter raises ValueError."""
    import asyncio
    connector = ESSLCardReaderConnector(essl_config)

    # Negative value
    with pytest.raises(ValueError, match="n_records must be positive"):
        asyncio.run(connector.get_sample_data(n_records=-5))

    # Zero value
    with pytest.raises(ValueError, match="n_records must be positive"):
        asyncio.run(connector.get_sample_data(n_records=0))

    # Too large
    with pytest.raises(ValueError, match="n_records too large"):
        asyncio.run(connector.get_sample_data(n_records=20000))
