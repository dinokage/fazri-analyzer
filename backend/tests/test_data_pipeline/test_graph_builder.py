"""Tests for graph building"""

import pytest
from backend.services.data_pipeline.tasks.graph_builder import build_graph_from_event


def test_build_person_graph():
    """Test building graph for person entity."""
    entity = {
        'entity_id': 'E100001',
        'entity_type': 'person',
        'raw_event': {
            'entity_id': 'E100001',
            'location_id': 'main_entrance',
            'timestamp': '2026-03-07 10:00:00',
            'event_type': 'card_swipe'
        }
    }

    result = build_graph_from_event.apply(args=[entity]).result

    assert result['status'] == 'success'
    assert result['nodes_created'] == 3
    assert result['relationships_created'] == 2
    assert result['entity_id'] == 'E100001'
    assert 'graph_structure' in result


def test_build_device_graph():
    """Test building graph for device entity."""
    entity = {
        'entity_id': 'abc123',
        'entity_type': 'device',
        'raw_event': {
            'device_hash': 'abc123',
            'location_id': 'ap_office',
            'timestamp': '2026-03-07 10:00:00',
            'event_type': 'wifi'
        }
    }

    result = build_graph_from_event.apply(args=[entity]).result

    assert result['status'] == 'success'
    assert result['nodes_created'] == 3
    assert result['relationships_created'] == 2
    assert result['entity_id'] == 'abc123'


def test_build_graph_unknown_type():
    """Test handling unknown entity type."""
    entity = {
        'entity_id': 'test123',
        'entity_type': 'unknown_type',
        'raw_event': {}
    }

    result = build_graph_from_event.apply(args=[entity]).result

    assert result['status'] == 'unknown_type'
    assert result['entity_type'] == 'unknown_type'


def test_build_person_graph_structure():
    """Test that person graph structure contains expected nodes and relationships."""
    entity = {
        'entity_id': 'E100002',
        'entity_type': 'person',
        'raw_event': {
            'entity_id': 'E100002',
            'location_id': 'library',
            'timestamp': '2026-03-07 14:30:00',
            'event_type': 'card_swipe'
        }
    }

    result = build_graph_from_event.apply(args=[entity]).result

    graph_structure = result['graph_structure']
    assert len(graph_structure['nodes']) == 3
    assert len(graph_structure['relationships']) == 2

    # Verify node types
    node_types = [node['type'] for node in graph_structure['nodes']]
    assert 'Person' in node_types
    assert 'Location' in node_types
    assert 'Event' in node_types

    # Verify relationship types
    rel_types = [rel['type'] for rel in graph_structure['relationships']]
    assert 'ACCESSED' in rel_types
    assert 'HAS_EVENT' in rel_types
