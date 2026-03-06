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
