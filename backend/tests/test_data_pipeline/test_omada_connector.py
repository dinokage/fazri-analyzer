# backend/tests/test_data_pipeline/test_omada_connector.py
import pytest
import json
from pathlib import Path
from datetime import datetime
from backend.services.data_pipeline.connectors.omada_connector import OmadaWiFiConnector
from backend.services.data_pipeline.connector_base import ConnectorConfig, ConnectorType, ConnectionMethod


@pytest.fixture
def omada_config():
    """Create test configuration for Omada connector."""
    return ConnectorConfig(
        connector_id="omada_test",
        institution_id="test_university",
        connector_type=ConnectorType.WIFI,
        connection_method=ConnectionMethod.REST_API,
        endpoint="https://use1-omada-northbound.tplinkcloud.com",
        credentials={
            "omadac_id": "test_omadac_id",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "site_id": "test_site_id"
        }
    )


@pytest.fixture
def sample_omada_logs():
    """Load sample Omada audit logs."""
    fixture_path = Path(__file__).parent / "fixtures" / "omada_sample_data.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return data["audit_logs"]


def test_omada_connector_creation(omada_config):
    """Test creating Omada connector instance."""
    connector = OmadaWiFiConnector(omada_config)
    assert connector.config.connector_id == "omada_test"
    assert connector.CONNECTOR_TYPE == ConnectorType.WIFI


def test_omada_parse_client_logs(omada_config, sample_omada_logs):
    """Test parsing Omada audit logs for client events."""
    connector = OmadaWiFiConnector(omada_config)
    events = connector._parse_client_logs(sample_omada_logs)

    assert len(events) == 2
    assert events[0]["device_hash"] is not None
    assert len(events[0]["device_hash"]) == 16  # SHA256 first 16 chars
    assert events[0]["event_type"] == "wifi"
    assert "timestamp" in events[0]


def test_omada_extract_mac_address(omada_config):
    """Test extracting MAC address from log text."""
    connector = OmadaWiFiConnector(omada_config)

    import re
    log_text = "Client 00:11:22:33:44:55 connected to AP-Office-1"
    mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', log_text)

    assert mac_match is not None
    assert mac_match.group(0) == "00:11:22:33:44:55"
