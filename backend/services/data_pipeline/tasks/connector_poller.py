"""
Connector Polling Service

Periodically polls active connectors to fetch new data.
Configured in celery_config.py beat_schedule to run every 5 minutes.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from dataclasses import asdict
from celery import group

from backend.services.data_pipeline.celery_app import app
from backend.services.data_pipeline.connector_base import ConnectorConfig, ConnectorType, ConnectionMethod
from backend.services.data_pipeline.connectors.essl_connector import ESSLCardReaderConnector
from backend.services.data_pipeline.connectors.omada_connector import OmadaWiFiConnector

logger = logging.getLogger(__name__)


# Mock connector registry (in production, this would come from database)
def get_active_connectors() -> List[ConnectorConfig]:
    """
    Get list of active connector configurations.

    In production, this would query a database table of configured connectors.
    For MVP, we return hardcoded configs that can be set via environment variables.
    """
    import os

    connectors = []

    # eSSL Card Reader Connector (if configured)
    if os.getenv('ESSL_ENABLED', 'false').lower() == 'true':
        connectors.append(ConnectorConfig(
            connector_id="essl_main",
            institution_id=os.getenv('INSTITUTION_ID', 'demo_university'),
            connector_type=ConnectorType.CARD_SWIPE,
            connection_method=ConnectionMethod.DATABASE,
            credentials={
                'host': os.getenv('ESSL_DB_HOST', 'localhost'),
                'port': int(os.getenv('ESSL_DB_PORT', '3306')),
                'username': os.getenv('ESSL_DB_USER', ''),
                'password': os.getenv('ESSL_DB_PASSWORD', ''),
                'database': os.getenv('ESSL_DB_NAME', ''),
                'table_name': os.getenv('ESSL_TABLE_NAME', 'AccessLogs')
            },
            field_mapping={
                'UserID': 'entity_id',
                'CardNo': 'card_id',
                'AccessTime': 'timestamp',
                'DoorID': 'location_id'
            },
            poll_interval=int(os.getenv('ESSL_POLL_INTERVAL', '300'))
        ))

    # Omada WiFi Connector (if configured)
    if os.getenv('OMADA_ENABLED', 'false').lower() == 'true':
        connectors.append(ConnectorConfig(
            connector_id="omada_main",
            institution_id=os.getenv('INSTITUTION_ID', 'demo_university'),
            connector_type=ConnectorType.WIFI,
            connection_method=ConnectionMethod.REST_API,
            endpoint=os.getenv('OMADA_ENDPOINT', 'https://use1-omada-northbound.tplinkcloud.com'),
            credentials={
                'omadac_id': os.getenv('OMADA_OMADAC_ID', ''),
                'client_id': os.getenv('OMADA_CLIENT_ID', ''),
                'client_secret': os.getenv('OMADA_CLIENT_SECRET', ''),
                'site_id': os.getenv('OMADA_SITE_ID', '')
            },
            poll_interval=int(os.getenv('OMADA_POLL_INTERVAL', '300'))
        ))

    return connectors


@app.task(name='services.data_pipeline.tasks.connector_poller.poll_all_connectors', queue='default', priority=5)
def poll_all_connectors():
    """
    Main polling task that runs every 5 minutes via Celery Beat.

    Fetches list of active connectors and triggers fetch tasks for each.
    """
    logger.info("Starting connector polling cycle")

    connectors = get_active_connectors()

    if not connectors:
        logger.warning("No active connectors configured")
        return {
            'status': 'no_connectors',
            'connectors_polled': 0
        }

    # Create group of fetch tasks (run in parallel)
    fetch_tasks = group([
        fetch_connector_data.s(asdict(connector))
        for connector in connectors
    ])

    # Execute all fetch tasks
    result = fetch_tasks.apply_async()

    logger.info(f"Triggered {len(connectors)} connector fetch tasks")

    return {
        'status': 'success',
        'connectors_polled': len(connectors),
        'connector_ids': [c.connector_id for c in connectors]
    }


@app.task(queue='default', priority=5)
async def fetch_connector_data(connector_config_dict: Dict[str, Any]):
    """
    Fetch data from a single connector and process it.

    Args:
        connector_config_dict: Serialized ConnectorConfig
    """
    from backend.services.data_pipeline.tasks.entity_resolution import resolve_entity

    # Reconstruct config from dict
    config = ConnectorConfig(**connector_config_dict)

    logger.info(f"Fetching data from connector: {config.connector_id}")

    try:
        # Instantiate appropriate connector
        if config.connector_type == ConnectorType.CARD_SWIPE:
            connector = ESSLCardReaderConnector(config)
        elif config.connector_type == ConnectorType.WIFI:
            connector = OmadaWiFiConnector(config)
        else:
            logger.error(f"Unsupported connector type: {config.connector_type}")
            return {'status': 'error', 'reason': 'unsupported_type'}

        # Calculate fetch window (fetch data since last successful poll)
        # For MVP, fetch last 10 minutes of data
        since = datetime.now(timezone.utc) - timedelta(minutes=10)

        # Fetch data
        raw_data = await connector.fetch_data(since)

        logger.info(f"Fetched {len(raw_data)} records from {config.connector_id}")

        # Normalize data
        normalized_data = connector.normalize_data(raw_data)

        # Send each event to entity resolution
        resolution_tasks = group([
            resolve_entity.s(event)
            for event in normalized_data
        ])

        resolution_tasks.apply_async()

        # Cleanup
        await connector.close()

        return {
            'status': 'success',
            'connector_id': config.connector_id,
            'records_fetched': len(raw_data),
            'records_normalized': len(normalized_data)
        }

    except Exception as e:
        logger.error(f"Error fetching from {config.connector_id}: {e}", exc_info=True)
        return {
            'status': 'error',
            'connector_id': config.connector_id,
            'error': str(e)
        }
