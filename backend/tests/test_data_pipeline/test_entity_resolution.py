"""Tests for entity resolution"""

import pytest
from unittest.mock import patch, MagicMock
from backend.services.data_pipeline.tasks.entity_resolution import resolve_entity


def test_resolve_entity_person():
    """Test resolving person entity from card swipe."""
    event = {
        'entity_id': 'E100001',
        'card_id': '1234567890',
        'timestamp': '2026-03-07 10:00:00',
        'location_id': 'main_entrance',
        'event_type': 'card_swipe'
    }

    # Mock the graph building task - patch where it's defined
    with patch('backend.services.data_pipeline.tasks.graph_builder.build_graph_from_event') as mock_graph:
        mock_graph.delay = MagicMock()
        result = resolve_entity.apply(args=[event]).result

        assert result['status'] == 'success'
        assert result['entity_type'] == 'person'
        mock_graph.delay.assert_called_once()


def test_resolve_entity_device():
    """Test resolving device entity from WiFi event."""
    event = {
        'device_hash': 'abc123def456',
        'timestamp': '2026-03-07 10:00:00',
        'location_id': 'ap_office_1',
        'event_type': 'wifi'
    }

    with patch('backend.services.data_pipeline.tasks.graph_builder.build_graph_from_event') as mock_graph:
        mock_graph.delay = MagicMock()
        result = resolve_entity.apply(args=[event]).result

        assert result['status'] == 'success'
        assert result['entity_type'] == 'device'


def test_resolve_entity_no_identifier():
    """Test handling event with no identifiable entity."""
    event = {
        'timestamp': '2026-03-07 10:00:00',
        'location_id': 'somewhere',
        'event_type': 'unknown'
    }

    with patch('backend.services.data_pipeline.tasks.graph_builder.build_graph_from_event') as mock_graph:
        mock_graph.delay = MagicMock()
        result = resolve_entity.apply(args=[event]).result

        assert result['status'] == 'no_entity'
        mock_graph.delay.assert_not_called()


def test_resolve_entity_card_id_only():
    """Test resolving person entity with only card_id (no entity_id)."""
    event = {
        'card_id': '9876543210',
        'timestamp': '2026-03-07 11:00:00',
        'location_id': 'side_entrance',
        'event_type': 'card_swipe'
    }

    with patch('backend.services.data_pipeline.tasks.graph_builder.build_graph_from_event') as mock_graph:
        mock_graph.delay = MagicMock()
        result = resolve_entity.apply(args=[event]).result

        assert result['status'] == 'success'
        assert result['entity_type'] == 'person'
        assert result['entity_id'] == '9876543210'
