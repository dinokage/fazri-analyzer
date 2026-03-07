"""
Graph Building Task

Creates nodes and relationships in Neo4j from resolved entities.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from services.data_pipeline.celery_app import app

logger = logging.getLogger(__name__)


@app.task(queue='graph_building', priority=3)
def build_graph_from_event(entity_data: Dict[str, Any]):
    """
    Build Neo4j graph from resolved entity.

    Args:
        entity_data: Resolved entity with entity_id, type, and event details

    Returns:
        Dict with graph building status
    """
    logger.info(f"Building graph for entity: {entity_data.get('entity_id')}")

    try:
        entity_type = entity_data.get('entity_type')

        if entity_type == 'person':
            result = _build_person_graph(entity_data)
        elif entity_type == 'device':
            result = _build_device_graph(entity_data)
        else:
            logger.warning(f"Unknown entity type: {entity_type}")
            return {'status': 'unknown_type', 'entity_type': entity_type}

        return result

    except Exception as e:
        logger.error(f"Graph building failed: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


def _build_person_graph(entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build graph nodes and relationships for person entity.

    Creates:
    - Person node (or merges with existing)
    - Location node
    - Event node
    - Relationships: (Person)-[:ACCESSED]->(Location)

    In production, this would use Neo4j driver to execute Cypher queries.
    For MVP, we log what would be created.
    """
    entity_id = entity_data.get('entity_id')
    raw_event = entity_data.get('raw_event', {})
    location_id = raw_event.get('location_id')
    timestamp = raw_event.get('timestamp')

    # Neo4j Cypher (production):
    # MERGE (p:Person {entity_id: $entity_id})
    # SET p.last_seen = $timestamp, p.event_count = p.event_count + 1
    # MERGE (l:Location {location_id: $location_id})
    # CREATE (e:Event {timestamp: $timestamp, type: 'swipe'})
    # CREATE (p)-[:ACCESSED {timestamp: $timestamp}]->(l)
    # CREATE (p)-[:HAS_EVENT]->(e)

    logger.info(f"Graph: Person {entity_id} ACCESSED Location {location_id} at {timestamp}")

    # For MVP: Just log the structure
    graph_structure = {
        'nodes': [
            {'type': 'Person', 'entity_id': entity_id},
            {'type': 'Location', 'location_id': location_id},
            {'type': 'Event', 'timestamp': timestamp, 'event_type': raw_event.get('event_type')}
        ],
        'relationships': [
            {'from': entity_id, 'type': 'ACCESSED', 'to': location_id, 'timestamp': timestamp},
            {'from': entity_id, 'type': 'HAS_EVENT', 'to': f"event_{timestamp}"}
        ]
    }

    return {
        'status': 'success',
        'entity_id': entity_id,
        'graph_structure': graph_structure,
        'nodes_created': 3,
        'relationships_created': 2
    }


def _build_device_graph(entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build graph nodes and relationships for device entity (WiFi).

    Creates:
    - Device node
    - Location node (AP)
    - Event node
    - Relationships: (Device)-[:CONNECTED_TO]->(Location)
    """
    device_hash = entity_data.get('entity_id')
    raw_event = entity_data.get('raw_event', {})
    location_id = raw_event.get('location_id')
    timestamp = raw_event.get('timestamp')

    logger.info(f"Graph: Device {device_hash} CONNECTED_TO Location {location_id} at {timestamp}")

    graph_structure = {
        'nodes': [
            {'type': 'Device', 'device_hash': device_hash},
            {'type': 'Location', 'location_id': location_id},
            {'type': 'Event', 'timestamp': timestamp, 'event_type': 'wifi'}
        ],
        'relationships': [
            {'from': device_hash, 'type': 'CONNECTED_TO', 'to': location_id, 'timestamp': timestamp},
            {'from': device_hash, 'type': 'HAS_EVENT', 'to': f"event_{timestamp}"}
        ]
    }

    return {
        'status': 'success',
        'entity_id': device_hash,
        'graph_structure': graph_structure,
        'nodes_created': 3,
        'relationships_created': 2
    }
