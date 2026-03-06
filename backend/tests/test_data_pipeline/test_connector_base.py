# backend/tests/test_data_pipeline/test_connector_base.py
import pytest
from datetime import datetime
from backend.services.data_pipeline.connector_base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorType,
    ConnectionMethod
)


def test_connector_config_creation():
    """Test creating a valid connector configuration"""
    config = ConnectorConfig(
        connector_id="test_connector",
        institution_id="demo_university",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        credentials={"host": "localhost"},
        field_mapping={"card_no": "card_id"}
    )

    assert config.connector_id == "test_connector"
    assert config.connector_type == ConnectorType.CARD_SWIPE
    assert config.is_active is True


def test_base_connector_abstract_methods():
    """Test that BaseConnector cannot be instantiated directly"""
    config = ConnectorConfig(
        connector_id="test",
        institution_id="test",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE
    )

    with pytest.raises(TypeError):
        BaseConnector(config)


def test_normalize_data_basic():
    """Test basic field mapping normalization."""
    config = ConnectorConfig(
        connector_id="test",
        institution_id="test",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        field_mapping={"card_no": "card_id", "student_id": "user_id"}
    )

    # Create a concrete implementation for testing
    class TestConnector(BaseConnector):
        async def test_connection(self) -> bool:
            return True
        async def fetch_data(self, since: datetime) -> list:
            return []
        async def get_sample_data(self, n_records: int = 10) -> list:
            return []

    connector = TestConnector(config)
    raw_data = [
        {"card_no": "12345", "student_id": "S001", "extra_field": "ignored"},
        {"card_no": "67890", "student_id": "S002"}
    ]

    result = connector.normalize_data(raw_data)

    assert len(result) == 2
    assert result[0] == {"card_id": "12345", "user_id": "S001"}
    assert result[1] == {"card_id": "67890", "user_id": "S002"}


def test_normalize_data_empty_mapping():
    """Test normalization with empty field mapping returns empty dicts."""
    config = ConnectorConfig(
        connector_id="test",
        institution_id="test",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        field_mapping={}  # Empty mapping
    )

    class TestConnector(BaseConnector):
        async def test_connection(self) -> bool:
            return True
        async def fetch_data(self, since: datetime) -> list:
            return []
        async def get_sample_data(self, n_records: int = 10) -> list:
            return []

    connector = TestConnector(config)
    raw_data = [{"card_no": "12345", "student_id": "S001"}]

    result = connector.normalize_data(raw_data)

    assert len(result) == 1
    assert result[0] == {}


def test_normalize_data_partial_fields():
    """Test normalization with partial field matches."""
    config = ConnectorConfig(
        connector_id="test",
        institution_id="test",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        field_mapping={"card_no": "card_id", "missing_field": "should_not_appear"}
    )

    class TestConnector(BaseConnector):
        async def test_connection(self) -> bool:
            return True
        async def fetch_data(self, since: datetime) -> list:
            return []
        async def get_sample_data(self, n_records: int = 10) -> list:
            return []

    connector = TestConnector(config)
    raw_data = [{"card_no": "12345"}]  # missing_field not in data

    result = connector.normalize_data(raw_data)

    assert len(result) == 1
    assert result[0] == {"card_id": "12345"}
    assert "should_not_appear" not in result[0]


def test_normalize_data_empty_input():
    """Test normalization with empty data list."""
    config = ConnectorConfig(
        connector_id="test",
        institution_id="test",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        field_mapping={"card_no": "card_id"}
    )

    class TestConnector(BaseConnector):
        async def test_connection(self) -> bool:
            return True
        async def fetch_data(self, since: datetime) -> list:
            return []
        async def get_sample_data(self, n_records: int = 10) -> list:
            return []

    connector = TestConnector(config)
    raw_data = []

    result = connector.normalize_data(raw_data)

    assert len(result) == 0
    assert result == []
