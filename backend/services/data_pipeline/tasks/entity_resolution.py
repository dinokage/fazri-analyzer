"""
Entity Resolution Task

Processes events to identify entities (people, devices) and resolve duplicates.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from backend.services.data_pipeline.celery_app import app

logger = logging.getLogger(__name__)


@app.task(queue='entity_resolution', priority=5)
def resolve_entity(event_data: Dict[str, Any]):
    """
    Resolve entity from event data.

    Args:
        event_data: Normalized event with fields like entity_id, card_id, device_hash, timestamp

    Returns:
        Dict with resolution status and entity ID
    """
    from backend.services.data_pipeline.tasks.graph_builder import build_graph_from_event

    logger.info(f"Resolving entity from event: {event_data.get('event_type', 'unknown')}")

    try:
        # Extract entity identifiers
        entity_id = event_data.get('entity_id')
        card_id = event_data.get('card_id')
        device_hash = event_data.get('device_hash')

        # Determine entity type
        if card_id or entity_id:
            resolved_entity = _resolve_person(event_data)
        elif device_hash:
            resolved_entity = _resolve_device(event_data)
        else:
            logger.warning(f"No identifiable entity in event: {event_data}")
            return {'status': 'no_entity', 'event_data': event_data}

        # Trigger graph building with resolved entity
        build_graph_from_event.delay(resolved_entity)

        return {
            'status': 'success',
            'entity_id': resolved_entity.get('entity_id'),
            'entity_type': resolved_entity.get('entity_type')
        }

    except Exception as e:
        logger.error(f"Entity resolution failed: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


def _resolve_person(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve person entity from card swipe or similar event.

    In production, this would:
    1. Query PostgreSQL entities table
    2. Check if card_id exists
    3. Create new entity or update existing
    4. Handle duplicates and merges

    For MVP, we create a simplified entity object.
    """
    entity_id = event_data.get('entity_id') or event_data.get('card_id')

    # In production: SELECT * FROM entities WHERE card_id = %s
    # For MVP: Create entity object
    entity = {
        'entity_id': entity_id,
        'entity_type': 'person',
        'card_id': event_data.get('card_id'),
        'first_seen': event_data.get('timestamp'),
        'last_seen': event_data.get('timestamp'),
        'event_count': 1,
        'source_dataset': event_data.get('source_dataset', 'unknown'),
        'raw_event': event_data
    }

    logger.info(f"Resolved person entity: {entity_id}")

    # In production: INSERT INTO entities (...) ON CONFLICT UPDATE
    # For MVP: Just return the entity

    return entity


def _resolve_device(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve device entity from WiFi or similar event.

    Similar to _resolve_person but for devices (MAC addresses, etc.)
    """
    device_hash = event_data.get('device_hash')

    entity = {
        'entity_id': device_hash,
        'entity_type': 'device',
        'device_hash': device_hash,
        'first_seen': event_data.get('timestamp'),
        'last_seen': event_data.get('timestamp'),
        'event_count': 1,
        'source_dataset': event_data.get('source_dataset', 'unknown'),
        'raw_event': event_data
    }

    logger.info(f"Resolved device entity: {device_hash}")

    return entity
