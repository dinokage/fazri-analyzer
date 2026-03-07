# backend/services/data_pipeline/celery_app.py
from celery import Celery
from kombu import Queue, Exchange

# Initialize Celery app
app = Celery('fazri_ingestion')

# Load configuration from config file
app.config_from_object('backend.services.data_pipeline.celery_config')

# Define task routes
app.conf.task_routes = {
    'backend.services.data_pipeline.tasks.entity_resolution.*': {
        'queue': 'entity_resolution',
        'priority': 5
    },
    'backend.services.data_pipeline.tasks.face_recognition.*': {
        'queue': 'face_recognition',
        'priority': 10  # Highest priority
    },
    'backend.services.data_pipeline.tasks.graph_builder.*': {
        'queue': 'graph_building',
        'priority': 3
    },
    'backend.services.data_pipeline.tasks.anomaly_detection.*': {
        'queue': 'anomaly_detection',
        'priority': 7
    },
}

# Auto-discover tasks
app.autodiscover_tasks([
    'backend.services.data_pipeline.tasks',
])

if __name__ == '__main__':
    app.start()
