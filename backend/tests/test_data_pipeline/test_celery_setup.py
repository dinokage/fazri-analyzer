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
    assert 'services.data_pipeline.tasks.face_recognition.*' in routes


def test_celery_queues_have_priorities():
    """Test that priority queues are configured."""
    queues = app.conf.task_queues
    assert queues is not None

    # Find face_recognition queue
    face_queue = next((q for q in queues if q.name == 'face_recognition'), None)
    assert face_queue is not None
    # Check priority is configured in queue_arguments
    assert face_queue.queue_arguments.get('x-max-priority') == 10
