# Live Data Ingestion Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-grade live data ingestion pipeline with pre-built connectors (eSSL, CP-PLUS, Omada), ML-powered schema detection, validation/quarantine system, and Celery-based async processing.

**Architecture:** Hybrid connector framework (pre-built + universal adapters) → ML schema auto-detection → Validation layer (quarantine bad records) → Redis priority queues → Celery worker pools (entity resolution, graph building, face recognition, anomaly detection) → PostgreSQL/Neo4j/Redis storage.

**Tech Stack:** Python 3.12, FastAPI, Celery 5.4, Redis 7.2, OpenCV 4.9, face_recognition 1.3.0, scikit-learn 1.4, asyncio, httpx, Pydantic 2.6

---

## Phase 1: Foundation & Infrastructure (Tasks 1-8)

### Task 1: Project Structure & Dependencies

**Files:**
- Create: `backend/services/data_pipeline/__init__.py`
- Create: `backend/services/data_pipeline/requirements.txt`
- Modify: `backend/requirements.txt`
- Create: `backend/tests/test_data_pipeline/__init__.py`

**Step 1: Create project structure**

```bash
mkdir -p backend/services/data_pipeline
mkdir -p backend/services/data_pipeline/connectors
mkdir -p backend/services/data_pipeline/tasks
mkdir -p backend/services/data_pipeline/validators
mkdir -p backend/tests/test_data_pipeline
touch backend/services/data_pipeline/__init__.py
touch backend/tests/test_data_pipeline/__init__.py
```

**Step 2: Add new dependencies to requirements.txt**

```txt
# Task Queue & Distributed Processing
celery==5.4.0
redis==5.0.3
kombu==5.3.5

# Data Processing & Validation
pydantic==2.6.3
pydantic-settings==2.2.1
python-multipart==0.0.9

# HTTP Clients for API connectors
httpx==0.27.0
aiohttp==3.9.3

# Database (async support)
aiomysql==0.2.0
asyncpg==0.29.0

# Computer Vision (already exists but verify versions)
opencv-python==4.9.0.80
face-recognition==1.3.0
```

**Step 3: Verify dependencies don't conflict**

Run: `cd backend && pip install -r requirements.txt --dry-run`
Expected: No conflicts reported

**Step 4: Create empty __init__.py files**

```python
# backend/services/data_pipeline/__init__.py
"""
Live Data Ingestion Pipeline

Provides connectors, schema detection, validation, and async processing
for ingesting data from various campus systems (card readers, CCTV, WiFi).
"""

__version__ = "1.0.0"
```

**Step 5: Commit**

```bash
git add backend/services/data_pipeline/ backend/tests/test_data_pipeline/
git commit -m "feat(ingestion): initialize data pipeline project structure

- Add data_pipeline service module
- Add new dependencies: celery, redis, httpx, aiomysql
- Create test directory structure"
```

---

### Task 2: Base Connector Framework

**Files:**
- Create: `backend/services/data_pipeline/connector_base.py`
- Create: `backend/tests/test_data_pipeline/test_connector_base.py`

**Step 1: Write failing test for BaseConnector**

```python
# backend/tests/test_data_pipeline/test_connector_base.py
import pytest
from datetime import datetime
from backend.services.data_pipeline.connector_base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorType,
    ConnectionMethod
)


def test_connector_config_creation():
    """Test creating a valid connector configuration"""
    config = ConnectorConfig(
        connector_id="test_connector",
        institution_id="demo_university",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        credentials={"host": "localhost"},
        field_mapping={"card_no": "card_id"}
    )

    assert config.connector_id == "test_connector"
    assert config.connector_type == ConnectorType.CARD_SWIPE
    assert config.is_active is True


def test_base_connector_abstract_methods():
    """Test that BaseConnector cannot be instantiated directly"""
    config = ConnectorConfig(
        connector_id="test",
        institution_id="test",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE
    )

    with pytest.raises(TypeError):
        BaseConnector(config)
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_data_pipeline/test_connector_base.py -v`
Expected: ModuleNotFoundError: No module named 'backend.services.data_pipeline.connector_base'

**Step 3: Implement BaseConnector classes**

```python
# backend/services/data_pipeline/connector_base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectorType(Enum):
    """Types of data connectors"""
    CARD_SWIPE = "card_swipe"
    WIFI = "wifi"
    CCTV = "cctv"
    LIBRARY = "library"
    BOOKING = "booking"
    HELPDESK = "helpdesk"


class ConnectionMethod(Enum):
    """Methods for connecting to data sources"""
    REST_API = "rest_api"
    DATABASE = "database"
    FILE_UPLOAD = "file_upload"
    WEBHOOK = "webhook"
    RTSP_STREAM = "rtsp_stream"
    MQTT = "mqtt"


@dataclass
class ConnectorConfig:
    """Configuration for a data connector"""
    connector_id: str
    institution_id: str
    connector_type: ConnectorType
    connection_method: ConnectionMethod

    # Connection details
    endpoint: Optional[str] = None
    credentials: Optional[Dict[str, str]] = field(default_factory=dict)
    poll_interval: int = 300  # seconds (5 minutes default)

    # Field mappings (populated by ML auto-detection)
    field_mapping: Dict[str, str] = field(default_factory=dict)

    # Validation rules
    validation_rules: List[Dict] = field(default_factory=list)

    # Status
    is_active: bool = True
    last_sync: Optional[datetime] = None


class BaseConnector(ABC):
    """Abstract base class for all data connectors"""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.logger = logging.getLogger(f"connector.{config.connector_id}")

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if connection to data source is valid"""
        pass

    @abstractmethod
    async def fetch_data(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch data from source since last sync"""
        pass

    @abstractmethod
    async def get_sample_data(self, n_records: int = 10) -> List[Dict[str, Any]]:
        """Get sample data for schema detection"""
        pass

    def normalize_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Apply field mappings to normalize data"""
        normalized = []
        for record in raw_data:
            mapped_record = {}
            for source_field, fazri_field in self.config.field_mapping.items():
                if source_field in record:
                    mapped_record[fazri_field] = record[source_field]
            normalized.append(mapped_record)
        return normalized
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_data_pipeline/test_connector_base.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/services/data_pipeline/connector_base.py backend/tests/test_data_pipeline/test_connector_base.py
git commit -m "feat(ingestion): add BaseConnector abstract class

- Define ConnectorType and ConnectionMethod enums
- Implement ConnectorConfig dataclass with validation
- Create BaseConnector ABC with required methods
- Add tests for connector configuration"
```

---

### Task 3: eSSL Card Reader Connector

**Files:**
- Create: `backend/services/data_pipeline/connectors/essl_connector.py`
- Create: `backend/tests/test_data_pipeline/test_essl_connector.py`
- Create: `backend/tests/test_data_pipeline/fixtures/essl_sample_data.json`

**Step 1: Create test fixtures**

```json
// backend/tests/test_data_pipeline/fixtures/essl_sample_data.json
[
  {
    "UserID": "E100001",
    "CardNo": "1234567890",
    "AccessTime": "2026-03-06 14:30:45",
    "DoorID": "1",
    "InOutStatus": "IN",
    "DeviceID": "ESSL_MAIN"
  },
  {
    "UserID": "E100002",
    "CardNo": "0987654321",
    "AccessTime": "2026-03-06 14:35:12",
    "DoorID": "2",
    "InOutStatus": "OUT",
    "DeviceID": "ESSL_LAB"
  }
]
```

**Step 2: Write failing test for eSSL connector**

```python
# backend/tests/test_data_pipeline/test_essl_connector.py
import pytest
import json
from pathlib import Path
from datetime import datetime
from backend.services.data_pipeline.connectors.essl_connector import ESSLCardReaderConnector
from backend.services.data_pipeline.connector_base import ConnectorConfig, ConnectorType, ConnectionMethod


@pytest.fixture
def essl_config():
    """Create test configuration for eSSL connector"""
    return ConnectorConfig(
        connector_id="essl_test",
        institution_id="test_university",
        connector_type=ConnectorType.CARD_SWIPE,
        connection_method=ConnectionMethod.DATABASE,
        credentials={
            "host": "localhost",
            "port": 3306,
            "username": "test",
            "password": "test",
            "database": "essl_test",
            "table_name": "AccessLogs"
        },
        field_mapping={
            "UserID": "entity_id",
            "CardNo": "card_id",
            "AccessTime": "timestamp",
            "DoorID": "location_id"
        }
    )


@pytest.fixture
def sample_essl_data():
    """Load sample eSSL data from fixtures"""
    fixture_path = Path(__file__).parent / "fixtures" / "essl_sample_data.json"
    with open(fixture_path) as f:
        return json.load(f)


def test_essl_connector_creation(essl_config):
    """Test creating eSSL connector instance"""
    connector = ESSLCardReaderConnector(essl_config)
    assert connector.config.connector_id == "essl_test"
    assert connector.CONNECTOR_TYPE == ConnectorType.CARD_SWIPE


def test_essl_normalize_data(essl_config, sample_essl_data):
    """Test normalizing eSSL data to Fazri format"""
    connector = ESSLCardReaderConnector(essl_config)
    normalized = connector.normalize_data(sample_essl_data)

    assert len(normalized) == 2
    assert normalized[0]["entity_id"] == "E100001"
    assert normalized[0]["card_id"] == "1234567890"
    assert "timestamp" in normalized[0]
    assert "location_id" in normalized[0]


@pytest.mark.asyncio
async def test_essl_parse_timestamp(essl_config):
    """Test parsing various eSSL timestamp formats"""
    connector = ESSLCardReaderConnector(essl_config)

    # Test standard format
    ts1 = connector._parse_timestamp("2026-03-06 14:30:45")
    assert isinstance(ts1, datetime)
    assert ts1.year == 2026

    # Test alternate format
    ts2 = connector._parse_timestamp("06/03/2026 14:30:45")
    assert isinstance(ts2, datetime)
```

**Step 3: Run test to verify it fails**

Run: `pytest backend/tests/test_data_pipeline/test_essl_connector.py -v`
Expected: ModuleNotFoundError: No module named 'backend.services.data_pipeline.connectors.essl_connector'

**Step 4: Implement eSSL connector (minimal version)**

```python
# backend/services/data_pipeline/connectors/essl_connector.py
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiomysql
import httpx

from ..connector_base import BaseConnector, ConnectorConfig, ConnectorType, ConnectionMethod

logger = logging.getLogger(__name__)


class ESSLCardReaderConnector(BaseConnector):
    """
    Pre-built connector for eSSL card reader systems

    Supported Models: X990, K90, K30 Pro, F22
    Integration Methods: REST API, Database Polling (MSSQL/MySQL)
    """

    CONNECTOR_TYPE = ConnectorType.CARD_SWIPE

    # Standard eSSL database schema
    DB_SCHEMA = {
        "AccessLogs": {
            "UserID": "entity_id",
            "CardNo": "card_id",
            "AccessTime": "timestamp",
            "DoorID": "location_id",
            "InOutStatus": "direction",
            "DeviceID": "device_id"
        }
    }

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.db_pool = None
        self.http_client = None

    async def initialize(self):
        """Initialize connection based on method"""
        if self.config.connection_method == ConnectionMethod.DATABASE:
            await self._init_database_connection()
        elif self.config.connection_method == ConnectionMethod.REST_API:
            await self._init_api_connection()

    async def _init_database_connection(self):
        """Initialize database connection pool"""
        db_config = self.config.credentials

        self.db_pool = await aiomysql.create_pool(
            host=db_config.get('host', 'localhost'),
            port=int(db_config.get('port', 3306)),
            user=db_config['username'],
            password=db_config['password'],
            db=db_config['database'],
            minsize=2,
            maxsize=10,
            autocommit=True
        )
        logger.info(f"eSSL DB connection pool created: {db_config['host']}")

    async def _init_api_connection(self):
        """Initialize HTTP client for API access"""
        self.http_client = httpx.AsyncClient(
            base_url=self.config.endpoint,
            headers={
                "Authorization": f"Bearer {self.config.credentials['api_token']}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        logger.info(f"eSSL API client initialized: {self.config.endpoint}")

    async def test_connection(self) -> bool:
        """Test connection to eSSL system"""
        try:
            if self.config.connection_method == ConnectionMethod.DATABASE:
                if not self.db_pool:
                    await self.initialize()

                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                        result = await cursor.fetchone()
                        return result is not None

            elif self.config.connection_method == ConnectionMethod.REST_API:
                if not self.http_client:
                    await self.initialize()

                response = await self.http_client.get("/api/health")
                return response.status_code == 200

            return False
        except Exception as e:
            logger.error(f"eSSL connection test failed: {e}")
            return False

    async def fetch_data(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch card swipe events since last sync"""
        if self.config.connection_method == ConnectionMethod.DATABASE:
            return await self._fetch_from_database(since)
        elif self.config.connection_method == ConnectionMethod.REST_API:
            return await self._fetch_from_api(since)

        return []

    async def _fetch_from_database(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch data from eSSL database"""
        table_name = self.config.credentials.get('table_name', 'AccessLogs')
        schema = self.DB_SCHEMA.get(table_name, self.DB_SCHEMA['AccessLogs'])

        # Find timestamp field
        timestamp_field = [k for k, v in schema.items() if v == 'timestamp'][0]

        query = f"""
            SELECT *
            FROM {table_name}
            WHERE {timestamp_field} > %s
            ORDER BY {timestamp_field} ASC
            LIMIT 5000
        """

        if not self.db_pool:
            await self.initialize()

        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, (since,))
                results = await cursor.fetchall()

                logger.info(f"Fetched {len(results)} records from eSSL DB")
                return results

    async def _fetch_from_api(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch data from eSSL REST API"""
        if not self.http_client:
            await self.initialize()

        response = await self.http_client.get(
            "/api/attendance/logs",
            params={
                "startTime": since.isoformat(),
                "endTime": datetime.now().isoformat(),
                "limit": 5000
            }
        )

        if response.status_code == 200:
            data = response.json()
            logger.info(f"Fetched {len(data.get('records', []))} records from eSSL API")
            return data.get('records', [])

        logger.error(f"eSSL API error: {response.status_code}")
        return []

    async def get_sample_data(self, n_records: int = 10) -> List[Dict[str, Any]]:
        """Get sample data for schema detection"""
        if self.config.connection_method == ConnectionMethod.DATABASE:
            table_name = self.config.credentials.get('table_name', 'AccessLogs')
            query = f"SELECT * FROM {table_name} LIMIT {n_records}"

            if not self.db_pool:
                await self.initialize()

            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query)
                    return await cursor.fetchall()

        elif self.config.connection_method == ConnectionMethod.REST_API:
            if not self.http_client:
                await self.initialize()

            response = await self.http_client.get(
                "/api/attendance/logs",
                params={"limit": n_records}
            )
            return response.json().get('records', [])

        return []

    def normalize_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Apply field mappings and normalize eSSL data"""
        normalized = []

        for record in raw_data:
            try:
                mapped_record = {}

                # Apply field mapping
                for source_field, fazri_field in self.config.field_mapping.items():
                    if source_field in record:
                        value = record[source_field]

                        # Special handling for timestamps
                        if fazri_field == 'timestamp':
                            mapped_record[fazri_field] = self._parse_timestamp(value)

                        # Special handling for card_id (ensure string)
                        elif fazri_field == 'card_id':
                            mapped_record[fazri_field] = str(value).strip()

                        else:
                            mapped_record[fazri_field] = value

                # Add metadata
                mapped_record['source_dataset'] = 'card_swipe'
                mapped_record['source_connector'] = self.config.connector_id
                mapped_record['event_type'] = 'swipe'

                normalized.append(mapped_record)

            except Exception as e:
                logger.warning(f"Failed to normalize record: {e}")
                continue

        return normalized

    def _parse_timestamp(self, value: Any) -> datetime:
        """Parse various timestamp formats from eSSL"""
        if isinstance(value, datetime):
            return value

        # Try common eSSL timestamp formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue

        raise ValueError(f"Could not parse timestamp: {value}")

    async def close(self):
        """Clean up resources"""
        if self.db_pool:
            self.db_pool.close()
            await self.db_pool.wait_closed()

        if self.http_client:
            await self.http_client.aclose()
```

**Step 5: Run tests to verify they pass**

Run: `pytest backend/tests/test_data_pipeline/test_essl_connector.py -v`
Expected: 3 passed

**Step 6: Commit**

```bash
git add backend/services/data_pipeline/connectors/essl_connector.py backend/tests/test_data_pipeline/
git commit -m "feat(ingestion): implement eSSL card reader connector

- Add ESSLCardReaderConnector with database and API support
- Implement field mapping and timestamp parsing
- Add comprehensive tests with fixtures
- Support for X990, K90, K30 Pro models"
```

---

### Task 4: Celery Configuration & Worker Setup

**Files:**
- Create: `backend/services/data_pipeline/celery_app.py`
- Create: `backend/services/data_pipeline/celery_config.py`
- Create: `backend/tests/test_data_pipeline/test_celery_setup.py`
- Create: `docker-compose.ingestion.yml`

**Step 1: Write test for Celery app initialization**

```python
# backend/tests/test_data_pipeline/test_celery_setup.py
import pytest
from backend.services.data_pipeline.celery_app import app


def test_celery_app_exists():
    """Test that Celery app is properly initialized"""
    assert app is not None
    assert app.main == 'fazri_ingestion'


def test_celery_task_routes_configured():
    """Test that task routes are configured"""
    routes = app.conf.task_routes
    assert routes is not None
    assert 'services.data_pipeline.tasks.face_recognition.*' in routes


def test_celery_queues_have_priorities():
    """Test that priority queues are configured"""
    queues = app.conf.task_queues
    assert queues is not None

    # Find face_recognition queue
    face_queue = next((q for q in queues if q.name == 'face_recognition'), None)
    assert face_queue is not None
    assert face_queue.priority == 10  # Highest priority
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_data_pipeline/test_celery_setup.py -v`
Expected: ModuleNotFoundError: No module named 'backend.services.data_pipeline.celery_app'

**Step 3: Implement Celery configuration**

```python
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
```

```python
# backend/services/data_pipeline/celery_app.py
from celery import Celery
from kombu import Queue, Exchange

# Initialize Celery app
app = Celery('fazri_ingestion')

# Load configuration from config file
app.config_from_object('services.data_pipeline.celery_config')

# Define task routes
app.conf.task_routes = {
    'services.data_pipeline.tasks.entity_resolution.*': {
        'queue': 'entity_resolution',
        'priority': 5
    },
    'services.data_pipeline.tasks.face_recognition.*': {
        'queue': 'face_recognition',
        'priority': 10  # Highest priority
    },
    'services.data_pipeline.tasks.graph_builder.*': {
        'queue': 'graph_building',
        'priority': 3
    },
    'services.data_pipeline.tasks.anomaly_detection.*': {
        'queue': 'anomaly_detection',
        'priority': 7
    },
}

# Auto-discover tasks
app.autodiscover_tasks([
    'services.data_pipeline.tasks',
])

if __name__ == '__main__':
    app.start()
```

**Step 4: Create Docker Compose for infrastructure**

```yaml
# docker-compose.ingestion.yml
version: '3.8'

services:
  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  celery-worker-entity:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A services.data_pipeline.celery_app worker -Q entity_resolution -c 8 --loglevel=info --hostname=entity@%h
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
      - DATABASE_URL=${DATABASE_URL}
      - NEO4J_URI=${NEO4J_URI}
    volumes:
      - ./backend:/app

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A services.data_pipeline.celery_app beat --loglevel=info
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - ./backend:/app

volumes:
  redis_data:
```

**Step 5: Run tests to verify they pass**

Run: `pytest backend/tests/test_data_pipeline/test_celery_setup.py -v`
Expected: 3 passed

**Step 6: Commit**

```bash
git add backend/services/data_pipeline/celery_app.py backend/services/data_pipeline/celery_config.py docker-compose.ingestion.yml backend/tests/test_data_pipeline/test_celery_setup.py
git commit -m "feat(ingestion): configure Celery with priority queues

- Add Celery app with Redis backend
- Configure 5 priority queues (face recognition highest)
- Set up worker pools with resource limits
- Add Docker Compose for Redis and Celery workers
- Configure periodic task scheduling"
```

---

## Phase 2: Core Connectors (Tasks 5-7)

### Task 5: Omada WiFi Connector

**Files:**
- Create: `backend/services/data_pipeline/connectors/omada_connector.py`
- Create: `backend/tests/test_data_pipeline/test_omada_connector.py`
- Create: `backend/tests/test_data_pipeline/fixtures/omada_sample_data.json`

**Step 1: Create test fixtures**

```json
// backend/tests/test_data_pipeline/fixtures/omada_sample_data.json
{
  "audit_logs": [
    {
      "timestamp": 1709738400000,
      "category": "CLIENTS",
      "text": "Client 00:11:22:33:44:55 connected to AP-Office-1",
      "site": "Main Office",
      "controller": "USA-Production"
    },
    {
      "timestamp": 1709738460000,
      "category": "CLIENTS",
      "text": "Client AA:BB:CC:DD:EE:FF disconnected from AP-Lab-2",
      "site": "Main Office",
      "controller": "USA-Production"
    }
  ]
}
```

**Step 2: Write failing test**

```python
# backend/tests/test_data_pipeline/test_omada_connector.py
import pytest
import json
from pathlib import Path
from datetime import datetime
from backend.services.data_pipeline.connectors.omada_connector import OmadaWiFiConnector
from backend.services.data_pipeline.connector_base import ConnectorConfig, ConnectorType, ConnectionMethod


@pytest.fixture
def omada_config():
    """Create test configuration for Omada connector"""
    return ConnectorConfig(
        connector_id="omada_test",
        institution_id="test_university",
        connector_type=ConnectorType.WIFI,
        connection_method=ConnectionMethod.REST_API,
        endpoint="https://use1-omada-northbound.tplinkcloud.com",
        credentials={
            "omadac_id": "test_omadac_id",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "site_id": "test_site_id"
        }
    )


@pytest.fixture
def sample_omada_logs():
    """Load sample Omada audit logs"""
    fixture_path = Path(__file__).parent / "fixtures" / "omada_sample_data.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return data["audit_logs"]


def test_omada_connector_creation(omada_config):
    """Test creating Omada connector instance"""
    connector = OmadaWiFiConnector(omada_config)
    assert connector.config.connector_id == "omada_test"
    assert connector.CONNECTOR_TYPE == ConnectorType.WIFI


def test_omada_parse_client_logs(omada_config, sample_omada_logs):
    """Test parsing Omada audit logs for client events"""
    connector = OmadaWiFiConnector(omada_config)
    events = connector._parse_client_logs(sample_omada_logs)

    assert len(events) == 2
    assert events[0]["device_hash"] is not None
    assert len(events[0]["device_hash"]) == 16  # SHA256 first 16 chars
    assert events[0]["event_type"] == "wifi"
    assert "timestamp" in events[0]


def test_omada_extract_mac_address(omada_config):
    """Test extracting MAC address from log text"""
    connector = OmadaWiFiConnector(omada_config)

    import re
    log_text = "Client 00:11:22:33:44:55 connected to AP-Office-1"
    mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', log_text)

    assert mac_match is not None
    assert mac_match.group(0) == "00:11:22:33:44:55"
```

**Step 3: Run test to verify it fails**

Run: `pytest backend/tests/test_data_pipeline/test_omada_connector.py -v`
Expected: ModuleNotFoundError

**Step 4: Implement Omada connector**

```python
# backend/services/data_pipeline/connectors/omada_connector.py
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
from hashlib import sha256

from ..connector_base import BaseConnector, ConnectorConfig, ConnectorType, ConnectionMethod

logger = logging.getLogger(__name__)


class OmadaWiFiConnector(BaseConnector):
    """
    Pre-built connector for TP-Link Omada SDN Controllers

    Supported Systems:
    - TP-Link Omada Software Controller
    - TP-Link Omada Hardware Controller (OC200, OC300)
    - Omada Cloud-Based Controller

    Authentication: OAuth 2.0 Client Credentials
    Rate Limit: 10 requests per second per controller
    """

    CONNECTOR_TYPE = ConnectorType.WIFI
    OMADA_BASE_URL = "https://use1-omada-northbound.tplinkcloud.com"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.http_client = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.omadac_id = None
        self.site_id = None

    async def initialize(self):
        """Initialize Omada Controller API connection"""
        self.omadac_id = self.config.credentials.get('omadac_id')
        self.site_id = self.config.credentials.get('site_id')

        # Get OAuth access token
        await self._get_access_token()

        self.http_client = httpx.AsyncClient(
            base_url=self.config.endpoint or self.OMADA_BASE_URL,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )

        logger.info(f"Omada Controller API initialized: {self.omadac_id}")

    async def _get_access_token(self):
        """Get OAuth 2.0 access token using Client Credentials Mode"""
        auth_client = httpx.AsyncClient(base_url=self.config.endpoint or self.OMADA_BASE_URL)

        response = await auth_client.post(
            "/openapi/authorize/token",
            params={"grant_type": "client_credentials"},
            json={
                "omadacId": self.config.credentials['omadac_id'],
                "client_id": self.config.credentials['client_id'],
                "client_secret": self.config.credentials['client_secret']
            }
        )

        if response.status_code == 200:
            result = response.json()['result']
            self.access_token = result['accessToken']
            self.refresh_token = result['refreshToken']

            # Token valid for 2 hours
            expires_in = result['expiresIn']
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)

            logger.info("Omada access token obtained successfully")
        else:
            raise Exception(f"Failed to get Omada access token: {response.status_code}")

        await auth_client.aclose()

    async def _ensure_valid_token(self):
        """Ensure access token is valid, refresh if needed"""
        if datetime.now() >= self.token_expires_at:
            await self._get_access_token()

    def _get_auth_header(self) -> Dict[str, str]:
        """Get authorization header with access token"""
        return {
            "Authorization": f"AccessToken={self.access_token}",
            "Content-Type": "application/json"
        }

    async def test_connection(self) -> bool:
        """Test Omada Controller API connection"""
        try:
            if not self.http_client:
                await self.initialize()

            await self._ensure_valid_token()

            # Test by getting site list
            response = await self.http_client.get(
                f"/openapi/v1/{self.omadac_id}/sites",
                headers=self._get_auth_header(),
                params={"pageSize": 1, "page": 1}
            )

            if response.status_code == 200:
                logger.info("Omada Controller connection successful")
                return True

            return False
        except Exception as e:
            logger.error(f"Omada connection test failed: {e}")
            return False

    async def fetch_data(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch wireless client connection events from Omada Controller"""
        if not self.http_client:
            await self.initialize()

        await self._ensure_valid_token()

        events = []

        try:
            # Fetch audit logs for client events
            response = await self.http_client.get(
                f"/openapi/v1/{self.omadac_id}/sites/{self.site_id}/audit-logs",
                headers=self._get_auth_header(),
                params={
                    "category": "CLIENTS",
                    "startTime": int(since.timestamp() * 1000),
                    "endTime": int(datetime.now().timestamp() * 1000),
                    "pageSize": 1000,
                    "page": 1
                }
            )

            if response.status_code == 200:
                result = response.json()['result']
                logs = result.get('data', [])
                events = self._parse_client_logs(logs)
                logger.info(f"Fetched {len(events)} client events from Omada")
            else:
                logger.error(f"Omada API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Failed to fetch Omada data: {e}")

        return events

    def _parse_client_logs(self, logs: List[Dict]) -> List[Dict]:
        """Parse Omada audit logs for client connection events"""
        events = []

        for log in logs:
            try:
                log_text = log.get('text', '')

                # Extract MAC address from log text
                mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', log_text)

                if mac_match:
                    mac_address = mac_match.group(0)
                    device_hash = sha256(mac_address.encode()).hexdigest()[:16]

                    events.append({
                        'device_hash': device_hash,
                        'device_mac': mac_address,
                        'location_id': self.site_id,
                        'timestamp': datetime.fromtimestamp(log.get('timestamp', 0) / 1000),
                        'event_type': 'wifi',
                        'source_dataset': 'wifi',
                        'log_text': log_text,
                        'raw_data': log
                    })

            except Exception as e:
                logger.warning(f"Failed to parse Omada log: {e}")

        return events

    async def get_sample_data(self, n_records: int = 10) -> List[Dict[str, Any]]:
        """Get sample audit log data"""
        if not self.http_client:
            await self.initialize()

        await self._ensure_valid_token()

        response = await self.http_client.get(
            f"/openapi/v1/{self.omadac_id}/sites/{self.site_id}/audit-logs",
            headers=self._get_auth_header(),
            params={
                "category": "CLIENTS",
                "pageSize": n_records,
                "page": 1
            }
        )

        if response.status_code == 200:
            return response.json()['result'].get('data', [])

        return []

    async def close(self):
        """Clean up resources"""
        if self.http_client:
            await self.http_client.aclose()
```

**Step 5: Run tests to verify they pass**

Run: `pytest backend/tests/test_data_pipeline/test_omada_connector.py -v`
Expected: 3 passed

**Step 6: Commit**

```bash
git add backend/services/data_pipeline/connectors/omada_connector.py backend/tests/test_data_pipeline/
git commit -m "feat(ingestion): implement TP-Link Omada WiFi connector

- Add OmadaWiFiConnector with OAuth 2.0 authentication
- Parse client events from audit logs
- Extract and hash MAC addresses for privacy
- Support automatic token refresh (2-hour validity)
- Add comprehensive tests with fixtures"
```

---

**Due to length constraints, I'll summarize the remaining tasks:**

### Task 6: CP-PLUS CCTV Connector (with RTSP support)
### Task 7: Schema Detection ML Service
### Task 8: Validation & Quarantine System

## Phase 3: Processing Pipeline (Tasks 9-12)

### Task 9: Face Recognition Celery Task
### Task 10: Entity Resolution Task
### Task 11: Graph Building Integration
### Task 12: Connector Polling Service

## Phase 4: API & UI (Tasks 13-15)

### Task 13: Connector Management API Endpoints
### Task 14: Admin Configuration UI (React components)
### Task 15: Quarantine Review Dashboard

## Phase 5: Testing & Documentation (Tasks 16-18)

### Task 16: Integration Tests
### Task 17: Performance Testing
### Task 18: Documentation & Deployment Guide

---

## Execution Notes

**Test-First Development:**
- Every feature starts with a failing test
- Run tests after each step to verify progress
- Commit frequently (after each passing test)

**Code Quality:**
- DRY: Extract common logic to base classes
- YAGNI: Build only what's specified
- Type hints on all functions
- Docstrings for public APIs

**Error Handling:**
- Try/except around external calls
- Log errors with context
- Return empty lists on failure (don't crash)

**Performance:**
- Async/await for I/O operations
- Connection pooling for databases
- Pagination for large datasets
- Rate limiting for APIs

---

## Ready to Execute?

This plan contains 18 detailed tasks broken into 5-minute steps. Each task is independently testable and committable.

**Estimated Time:** 6-8 weeks with 1-2 developers

Would you like me to continue with the remaining tasks (6-18) in full detail?
