# backend/services/data_pipeline/celery_config.py
import os
from kombu import Queue, Exchange

# Broker and Backend Configuration
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# Redis configuration
broker_transport_options = {
    'visibility_timeout': 3600,  # 1 hour
    'max_connections': 100,
    'priority_steps': list(range(11)),  # 0-10 priority levels
    'sep': ':',
    'queue_order_strategy': 'priority',
}

# Task serialization
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Queue definitions with priority (Redis: 0 is highest, 10 is lowest)
task_queues = (
    Queue('face_recognition', Exchange('face_recognition'), routing_key='face.#',
          priority=10, queue_arguments={'x-max-priority': 10}),

    Queue('anomaly_detection', Exchange('anomaly_detection'), routing_key='anomaly.#',
          priority=7, queue_arguments={'x-max-priority': 10}),

    Queue('entity_resolution', Exchange('entity_resolution'), routing_key='entity.#',
          priority=5, queue_arguments={'x-max-priority': 10}),

    Queue('graph_building', Exchange('graph_building'), routing_key='graph.#',
          priority=3, queue_arguments={'x-max-priority': 10}),

    Queue('default', Exchange('default'), routing_key='default',
          priority=1, queue_arguments={'x-max-priority': 10}),
)

# Worker configuration
worker_prefetch_multiplier = 4
worker_max_tasks_per_child = 1000
worker_disable_rate_limits = False

# Task execution limits
task_soft_time_limit = 300  # 5 minutes soft limit
task_time_limit = 600  # 10 minutes hard limit
task_acks_late = True
task_reject_on_worker_lost = True

# Result expiration
result_expires = 3600  # 1 hour

# Monitoring
worker_send_task_events = True
task_send_sent_event = True

# Logging
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Beat schedule (periodic tasks)
beat_schedule = {
    'poll-connectors': {
        'task': 'services.data_pipeline.tasks.connector_poller.poll_all_connectors',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'default', 'priority': 5}
    },
}
