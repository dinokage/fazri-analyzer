"""Tests for connector polling service"""

import pytest
from unittest.mock import patch, MagicMock
import sys

# Mock the connectors module to avoid import errors
sys.modules['backend.services.data_pipeline.connector_base'] = MagicMock()
sys.modules['backend.services.data_pipeline.connectors.essl_connector'] = MagicMock()
sys.modules['backend.services.data_pipeline.connectors.omada_connector'] = MagicMock()

from services.data_pipeline.tasks.connector_poller import (
    poll_all_connectors,
    get_active_connectors
)


def test_get_active_connectors_empty():
    """Test getting active connectors when none configured."""
    with patch.dict('os.environ', {}, clear=True):
        connectors = get_active_connectors()
        assert len(connectors) == 0


def test_get_active_connectors_essl():
    """Test getting eSSL connector when configured."""
    with patch.dict('os.environ', {
        'ESSL_ENABLED': 'true',
        'ESSL_DB_HOST': 'localhost',
        'ESSL_DB_USER': 'test',
        'ESSL_DB_PASSWORD': 'test',
        'ESSL_DB_NAME': 'test_db'
    }):
        connectors = get_active_connectors()
        assert len(connectors) == 1
        assert connectors[0].connector_id == 'essl_main'


def test_get_active_connectors_omada():
    """Test getting Omada connector when configured."""
    with patch.dict('os.environ', {
        'OMADA_ENABLED': 'true',
        'OMADA_OMADAC_ID': 'test_id',
        'OMADA_CLIENT_ID': 'client123',
        'OMADA_CLIENT_SECRET': 'secret456',
        'OMADA_SITE_ID': 'site789'
    }):
        connectors = get_active_connectors()
        assert len(connectors) == 1
        assert connectors[0].connector_id == 'omada_main'


def test_get_active_connectors_both():
    """Test getting both connectors when configured."""
    with patch.dict('os.environ', {
        'ESSL_ENABLED': 'true',
        'ESSL_DB_HOST': 'localhost',
        'ESSL_DB_USER': 'test',
        'ESSL_DB_PASSWORD': 'test',
        'ESSL_DB_NAME': 'test_db',
        'OMADA_ENABLED': 'true',
        'OMADA_OMADAC_ID': 'test_id',
        'OMADA_CLIENT_ID': 'client123',
        'OMADA_CLIENT_SECRET': 'secret456',
        'OMADA_SITE_ID': 'site789'
    }):
        connectors = get_active_connectors()
        assert len(connectors) == 2
        connector_ids = [c.connector_id for c in connectors]
        assert 'essl_main' in connector_ids
        assert 'omada_main' in connector_ids


@patch('services.data_pipeline.tasks.connector_poller.group')
def test_poll_all_connectors_no_connectors(mock_group):
    """Test poll_all_connectors when no connectors configured."""
    with patch.dict('os.environ', {}, clear=True):
        result = poll_all_connectors()

        assert result['status'] == 'no_connectors'
        assert result['connectors_polled'] == 0
        mock_group.assert_not_called()


@patch('services.data_pipeline.tasks.connector_poller.group')
def test_poll_all_connectors_with_connectors(mock_group):
    """Test poll_all_connectors with active connectors."""
    mock_result = MagicMock()
    mock_group.return_value.apply_async.return_value = mock_result

    with patch.dict('os.environ', {
        'ESSL_ENABLED': 'true',
        'ESSL_DB_HOST': 'localhost',
        'ESSL_DB_USER': 'test',
        'ESSL_DB_PASSWORD': 'test',
        'ESSL_DB_NAME': 'test_db'
    }):
        result = poll_all_connectors()

        assert result['status'] == 'success'
        assert result['connectors_polled'] == 1
        assert 'essl_main' in result['connector_ids']
        mock_group.assert_called_once()
