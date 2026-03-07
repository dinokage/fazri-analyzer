# backend/tests/test_data_pipeline/test_celery_setup.py
import pytest
from backend.services.data_pipeline.celery_app import app


def test_celery_app_exists():
    """Test that Celery app is properly initialized."""
    assert app is not None
    assert app.main == 'fazri_ingestion'


def test_celery_task_routes_configured():
    """Test that task routes are configured."""
    routes = app.conf.task_routes
    assert routes is not None
    assert 'backend.services.data_pipeline.tasks.face_recognition.*' in routes


def test_celery_queues_have_priorities():
    """Test that priority queues are configured."""
    queues = app.conf.task_queues
    assert queues is not None
    assert len(queues) == 5  # Verify all 5 queues exist

    # Create a dict of queues by name for easy lookup
    queue_dict = {q.name: q for q in queues}

    # Test face_recognition queue (highest priority)
    assert 'face_recognition' in queue_dict
    face_queue = queue_dict['face_recognition']
    assert face_queue.queue_arguments.get('x-max-priority') == 10

    # Test anomaly_detection queue
    assert 'anomaly_detection' in queue_dict
    anomaly_queue = queue_dict['anomaly_detection']
    assert anomaly_queue.queue_arguments.get('x-max-priority') == 10

    # Test entity_resolution queue
    assert 'entity_resolution' in queue_dict
    entity_queue = queue_dict['entity_resolution']
    assert entity_queue.queue_arguments.get('x-max-priority') == 10

    # Test graph_building queue
    assert 'graph_building' in queue_dict
    graph_queue = queue_dict['graph_building']
    assert graph_queue.queue_arguments.get('x-max-priority') == 10

    # Test default queue (lowest priority)
    assert 'default' in queue_dict
    default_queue = queue_dict['default']
    assert default_queue.queue_arguments.get('x-max-priority') == 10


def test_celery_beat_schedule_configured():
    """Test that periodic tasks are configured in beat schedule."""
    beat_schedule = app.conf.beat_schedule
    assert beat_schedule is not None

    # Check poll-connectors task
    assert 'poll-connectors' in beat_schedule
    poll_task = beat_schedule['poll-connectors']
    assert poll_task['task'] == 'backend.services.data_pipeline.tasks.connector_poller.poll_all_connectors'
    assert poll_task['schedule'] == 300.0  # Every 5 minutes
    assert poll_task['options']['queue'] == 'default'
    assert poll_task['options']['priority'] == 5
