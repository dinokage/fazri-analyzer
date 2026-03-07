"""Pytest configuration for data pipeline tests."""

import pytest
from celery import Celery


@pytest.fixture(scope='session', autouse=True)
def celery_config():
    """Configure Celery for testing."""
    return {
        'broker_url': 'memory://',
        'result_backend': 'cache+memory://',
        'task_always_eager': True,
        'task_eager_propagates': True,
    }


@pytest.fixture(scope='session')
def celery_app(celery_config):
    """Create a Celery app for testing."""
    from backend.services.data_pipeline.celery_app import app

    # Override config for testing
    app.conf.update(celery_config)

    return app
