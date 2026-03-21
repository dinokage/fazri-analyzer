# Live Data Ingestion Pipeline - Complete Implementation Guide

**Version:** 1.0
**Last Updated:** March 6, 2026
**Target Completion:** 8 weeks

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Pre-built Connector Implementations](#pre-built-connector-implementations)
5. [Universal Adapter Framework](#universal-adapter-framework)
6. [ML-Powered Schema Detection](#ml-powered-schema-detection)
7. [Validation & Quarantine System](#validation--quarantine-system)
8. [Celery Worker Configuration](#celery-worker-configuration)
9. [Face Recognition Pipeline](#face-recognition-pipeline)
10. [Implementation Roadmap](#implementation-roadmap)
11. [API Documentation & Resources](#api-documentation--resources)

---

## Executive Summary

This guide provides a complete implementation plan for building a **live data ingestion pipeline** that makes Fazri Analyzer deployable at any institution with minimal configuration. The system supports:

- **3 Priority Data Sources**: Card swipes (eSSL), CCTV (CP-PLUS), WiFi (Cisco/Aruba)
- **Micro-batch Architecture**: 5-7 minute processing latency
- **Hybrid Connector Approach**: Pre-built connectors + universal adapters
- **ML-Powered Schema Mapping**: Auto-detection with admin confirmation
- **Production-Grade Validation**: Quarantine system for bad records
- **Scalable Processing**: Celery workers with Redis backend

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  INSTITUTION INFRASTRUCTURE                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  eSSL Card   │  │  CP-PLUS     │  │ Cisco/Aruba  │          │
│  │  Readers     │  │  CCTV NVR    │  │ WiFi Ctrl    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │      INGESTION CONNECTOR LAYER      │
          │  ┌───────────┐  ┌───────────────┐  │
          │  │ Pre-built │  │   Universal   │  │
          │  │Connectors │  │   Adapters    │  │
          │  └─────┬─────┘  └───────┬───────┘  │
          └────────┼────────────────┼───────────┘
                   │                │
                   ▼                ▼
          ┌─────────────────────────────────────┐
          │   ML SCHEMA AUTO-DETECTION          │
          │   • Field type inference            │
          │   • Confidence scoring              │
          │   • Admin confirmation UI           │
          └────────────────┬────────────────────┘
                           │
                           ▼
          ┌─────────────────────────────────────┐
          │   VALIDATION & NORMALIZATION        │
          │   Valid → Processing Queue          │
          │   Invalid → Quarantine DB           │
          └────────────────┬────────────────────┘
                           │
                           ▼
          ┌─────────────────────────────────────┐
          │   REDIS PRIORITY QUEUES             │
          │   High: Card swipes (< 1 min)       │
          │   Medium: WiFi logs (< 5 min)       │
          │   Low: Other events (< 10 min)      │
          └────────────────┬────────────────────┘
                           │
                           ▼
          ┌─────────────────────────────────────┐
          │   CELERY WORKER POOLS               │
          │   • Entity Resolution (8 workers)   │
          │   • Graph Building (4 workers)      │
          │   • Face Recognition (4 GPU workers)│
          │   • Anomaly Detection (4 workers)   │
          └────────────────┬────────────────────┘
                           │
                           ▼
          ┌─────────────────────────────────────┐
          │   STORAGE LAYER                     │
          │   PostgreSQL | Neo4j | Redis | S3   │
          └─────────────────────────────────────┘
```

---

## Technology Stack

### Core Dependencies

```python
# backend/requirements.txt - NEW ADDITIONS

# Task Queue & Distributed Processing
celery==5.4.0
redis==5.0.3
kombu==5.3.5  # Celery's messaging library

# Data Processing & Validation
pydantic==2.6.3
pydantic-settings==2.2.1
python-multipart==0.0.9  # File uploads
sqlalchemy==2.0.28
alembic==1.13.1  # Database migrations

# Face Recognition & Computer Vision
opencv-python==4.9.0.80
face-recognition==1.3.0
dlib==19.24.2  # Required by face_recognition
Pillow==10.2.0

# ML for Schema Detection
scikit-learn==1.4.1
pandas==2.2.1
numpy==1.26.4

# HTTP Clients for API connectors
httpx==0.27.0  # Async HTTP client
aiohttp==3.9.3
requests==2.31.0

# Database Drivers (already in requirements)
psycopg2-binary==2.9.10  # PostgreSQL
neo4j==6.0.2  # Neo4j

# Monitoring & Logging
python-json-logger==2.0.7
sentry-sdk==1.40.6  # Error tracking
```

### Infrastructure Requirements

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

  celery-worker-entity:
    build: ./backend
    command: celery -A services.data_pipeline.celery_app worker -Q entity_resolution -c 8 --loglevel=info
    depends_on:
      - redis
      - postgres
      - neo4j
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
      - DATABASE_URL=${DATABASE_URL}
      - NEO4J_URI=${NEO4J_URI}
    volumes:
      - ./backend:/app

  celery-worker-face:
    build: ./backend
    command: celery -A services.data_pipeline.celery_app worker -Q face_recognition -c 4 --loglevel=info
    depends_on:
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1

  celery-beat:
    build: ./backend
    command: celery -A services.data_pipeline.celery_app beat --loglevel=info
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0

volumes:
  redis_data:
```

---

## Pre-built Connector Implementations

### 1. eSSL Card Reader Connector

**Supported Models:** X990, K90, K30 Pro, F22
**Integration Methods:** REST API, Database Polling (MSSQL/MySQL)

#### Implementation

```python
# backend/services/data_pipeline/connectors/essl_connector.py

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiomysql
import httpx
from hashlib import sha256

from ..connector_base import BaseConnector, ConnectorConfig, ConnectorType, ConnectionMethod

logger = logging.getLogger(__name__)


class ESSLCardReaderConnector(BaseConnector):
    """
    Pre-built connector for eSSL card reader systems

    Supported Integration Methods:
    1. Database Polling (MSSQL/MySQL) - eSSL stores logs in DB
    2. REST API (via AmpleTrails or Cams Biometrics bridge)
    3. Direct SDK integration (for on-premise installations)

    Resources:
    - AmpleTrails API: https://ampletrails.com/essl-biometric-api/
    - Cams Protocol: https://camsbiometrics.com/
    - eSSL Official: https://www.esslsecurity.com/software-integration
    """

    CONNECTOR_TYPE = ConnectorType.CARD_SWIPE

    # Standard eSSL database schema (varies by model)
    DB_SCHEMA = {
        "AccessLogs": {
            "UserID": "entity_id",
            "CardNo": "card_id",
            "AccessTime": "timestamp",
            "DoorID": "location_id",
            "InOutStatus": "direction",
            "DeviceID": "device_id"
        },
        # Alternative schema used by some eSSL models
        "AttendanceLog": {
            "EmpID": "entity_id",
            "CardNum": "card_id",
            "LogTime": "timestamp",
            "DeviceName": "location_id",
            "VerifyMode": "auth_method"
        }
    }

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.db_pool = None
        self.http_client = None
        self.last_sync_timestamp = config.last_sync or datetime.now()

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
                async with self.db_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                        result = await cursor.fetchone()
                        return result is not None

            elif self.config.connection_method == ConnectionMethod.REST_API:
                # Test API health endpoint
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
        # Determine which table schema to use
        table_name = self.config.credentials.get('table_name', 'AccessLogs')
        schema = self.DB_SCHEMA.get(table_name, self.DB_SCHEMA['AccessLogs'])

        # Build query
        timestamp_field = [k for k, v in schema.items() if v == 'timestamp'][0]

        query = f"""
            SELECT *
            FROM {table_name}
            WHERE {timestamp_field} > %s
            ORDER BY {timestamp_field} ASC
            LIMIT 5000
        """

        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, (since,))
                results = await cursor.fetchall()

                logger.info(f"Fetched {len(results)} records from eSSL DB")
                return results

    async def _fetch_from_api(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch data from eSSL REST API (AmpleTrails/Cams format)"""
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

            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query)
                    return await cursor.fetchall()

        elif self.config.connection_method == ConnectionMethod.REST_API:
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

                        # Special handling for location_id
                        elif fazri_field == 'location_id':
                            mapped_record[fazri_field] = self._map_door_to_location(value)

                        else:
                            mapped_record[fazri_field] = value

                # Add metadata
                mapped_record['source_dataset'] = 'card_swipe'
                mapped_record['source_connector'] = self.config.connector_id
                mapped_record['event_type'] = 'swipe'
                mapped_record['raw_data'] = record  # Keep for debugging

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

    def _map_door_to_location(self, door_id: Any) -> str:
        """Map door/device ID to location_id"""
        # This mapping should be configured per institution
        door_mapping = self.config.credentials.get('door_mapping', {})
        return door_mapping.get(str(door_id), f"DOOR_{door_id}")

    async def close(self):
        """Clean up resources"""
        if self.db_pool:
            self.db_pool.close()
            await self.db_pool.wait_closed()

        if self.http_client:
            await self.http_client.aclose()
```

#### Configuration Example

```yaml
# configs/institution_demo/essl_card_reader.yaml
connector:
  connector_id: "essl_main_entrance"
  institution_id: "demo_university"
  connector_type: "card_swipe"
  connection_method: "database"  # or "rest_api"

  # Database connection (if using database method)
  endpoint: null
  credentials:
    host: "192.168.1.100"
    port: 3306
    username: "essl_readonly"
    password: "${ESSL_DB_PASSWORD}"
    database: "essl_attendance"
    table_name: "AccessLogs"

    # Door to location mapping
    door_mapping:
      "1": "MAIN_ENTRANCE"
      "2": "LAB_101"
      "3": "LIBRARY_ENTRANCE"
      "4": "ADMIN_BUILDING"

  # API connection (if using API method)
  # endpoint: "https://api.ampletrails.com"
  # credentials:
  #   api_token: "${ESSL_API_TOKEN}"

  poll_interval: 300  # 5 minutes

  field_mapping:
    UserID: "entity_id"
    CardNo: "card_id"
    AccessTime: "timestamp"
    DoorID: "location_id"
    InOutStatus: "direction"

  is_active: true
```

---

### 2. CP-PLUS CCTV Connector

**Supported Models:** CP-UNR series with AI face detection
**Integration Methods:** HTTP API, RTSP Stream

#### Implementation

```python
# backend/services/data_pipeline/connectors/cpplus_connector.py

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
import cv2
import numpy as np
from urllib.parse import urlparse

from ..connector_base import BaseConnector, ConnectorConfig, ConnectorType, ConnectionMethod

logger = logging.getLogger(__name__)


class CPPlusCCTVConnector(BaseConnector):
    """
    Pre-built connector for CP-PLUS CCTV NVR systems with AI face detection

    Supported Models:
    - CP-UNR-216F2-I2 (16Ch AI NVR)
    - CP-UNR-4K5082-FI (8Ch 4K NVR with face recognition)
    - CP-UNR-4K4082-V4 (4K NVR with AI)

    Integration Methods:
    1. HTTP API - Face detection events from NVR
    2. RTSP Streaming - Real-time video processing
    3. ONVIF Protocol - Standard camera interface

    Resources:
    - CP-PLUS Products: https://www.cpplusworld.com/
    - ONVIF Spec: https://www.onvif.org/
    - iSpy CP-PLUS Setup: https://www.ispyconnect.com/camera/cp-plus

    Note: CP-PLUS doesn't provide public API docs. This connector uses:
    - ONVIF standard protocol for camera control
    - Direct RTSP stream access for video
    - Proprietary HTTP API (requires NVR firmware 2.0+)
    """

    CONNECTOR_TYPE = ConnectorType.CCTV

    # Default RTSP port for CP-PLUS NVRs
    DEFAULT_RTSP_PORT = 554

    # Camera to location mapping (configured per installation)
    camera_locations = {}

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.http_client = None
        self.active_streams = {}  # {camera_id: VideoCapture}
        self.face_detector = None

    async def initialize(self):
        """Initialize CP-PLUS NVR connection"""
        # Initialize HTTP client for API access
        self.http_client = httpx.AsyncClient(
            base_url=self.config.endpoint,
            auth=(
                self.config.credentials['username'],
                self.config.credentials['password']
            ),
            timeout=30.0,
            verify=False  # CP-PLUS often uses self-signed certs
        )

        # Load camera to location mapping
        self.camera_locations = self.config.credentials.get('camera_mapping', {})

        logger.info(f"CP-PLUS NVR initialized: {self.config.endpoint}")

    async def test_connection(self) -> bool:
        """Test connection to CP-PLUS NVR"""
        try:
            # Try to get system info via proprietary API
            response = await self.http_client.get(
                "/ISAPI/System/deviceInfo",
                timeout=10.0
            )

            if response.status_code == 200:
                logger.info("CP-PLUS NVR connection successful")
                return True

            # Fallback: Try ONVIF GetDeviceInformation
            response = await self.http_client.post(
                "/onvif/device_service",
                content=self._build_onvif_request("GetDeviceInformation")
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"CP-PLUS connection test failed: {e}")
            return False

    async def fetch_data(self, since: datetime) -> List[Dict[str, Any]]:
        """
        Fetch face detection events from CP-PLUS NVR

        CP-PLUS NVRs with AI face detection can:
        1. Store face detection events in internal database
        2. Send events via webhook (if configured)
        3. Query events via HTTP API
        """
        events = []

        # Method 1: Query face detection events via API
        try:
            response = await self.http_client.get(
                "/ISAPI/Smart/FaceDetection/events",
                params={
                    "startTime": since.isoformat(),
                    "endTime": datetime.now().isoformat()
                }
            )

            if response.status_code == 200:
                data = response.json()
                events = self._parse_face_events(data.get('events', []))

        except httpx.HTTPError as e:
            logger.warning(f"CP-PLUS API query failed, falling back to stream: {e}")

        return events

    def _parse_face_events(self, raw_events: List[Dict]) -> List[Dict]:
        """Parse face detection events from CP-PLUS format"""
        parsed_events = []

        for event in raw_events:
            try:
                parsed_events.append({
                    'camera_id': event.get('channelID'),
                    'timestamp': self._parse_cpplus_timestamp(event.get('dateTime')),
                    'face_snapshot_url': event.get('faceURL'),
                    'location_id': self._map_camera_to_location(event.get('channelID')),
                    'confidence': float(event.get('matchScore', 0.0)),
                    'event_type': 'cctv_sighting',
                    'source_dataset': 'cctv',
                    'raw_data': event
                })
            except Exception as e:
                logger.warning(f"Failed to parse CP-PLUS event: {e}")

        return parsed_events

    async def start_rtsp_stream_processing(self, camera_id: str):
        """
        Start processing RTSP stream from specific camera

        CP-PLUS RTSP URL format:
        rtsp://username:password@nvr_ip:554/cam/realmonitor?channel=1&subtype=0
        """
        rtsp_url = self._build_rtsp_url(camera_id)

        # This should run in a separate worker/thread
        logger.info(f"Starting RTSP stream processing: {rtsp_url}")

        # Queue this for Celery worker processing
        from ..tasks import process_rtsp_stream
        process_rtsp_stream.delay(
            connector_id=self.config.connector_id,
            camera_id=camera_id,
            rtsp_url=rtsp_url
        )

    def _build_rtsp_url(self, camera_id: str) -> str:
        """Build RTSP URL for CP-PLUS camera"""
        nvr_host = urlparse(self.config.endpoint).hostname
        username = self.config.credentials['username']
        password = self.config.credentials['password']

        # CP-PLUS RTSP URL format
        return (
            f"rtsp://{username}:{password}@{nvr_host}:{self.DEFAULT_RTSP_PORT}"
            f"/cam/realmonitor?channel={camera_id}&subtype=0"
        )

    def _map_camera_to_location(self, camera_id: str) -> str:
        """Map camera ID to physical location"""
        return self.camera_locations.get(
            str(camera_id),
            f"CAMERA_{camera_id}"
        )

    def _parse_cpplus_timestamp(self, ts_string: str) -> datetime:
        """Parse CP-PLUS timestamp format"""
        # CP-PLUS uses ISO format: 2024-03-06T14:30:45Z
        return datetime.fromisoformat(ts_string.replace('Z', '+00:00'))

    def _build_onvif_request(self, operation: str) -> str:
        """Build ONVIF SOAP request (fallback compatibility)"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
            <s:Body>
                <{operation} xmlns="http://www.onvif.org/ver10/device/wsdl"/>
            </s:Body>
        </s:Envelope>"""

    async def get_sample_data(self, n_records: int = 10) -> List[Dict[str, Any]]:
        """Get sample face detection events"""
        response = await self.http_client.get(
            "/ISAPI/Smart/FaceDetection/events",
            params={"limit": n_records}
        )

        if response.status_code == 200:
            return response.json().get('events', [])

        return []

    async def close(self):
        """Clean up resources"""
        if self.http_client:
            await self.http_client.aclose()

        # Stop all active RTSP streams
        for camera_id, stream in self.active_streams.items():
            if stream:
                stream.release()
```

#### RTSP Stream Processing Task

```python
# backend/services/data_pipeline/tasks/rtsp_processor.py

import cv2
import numpy as np
import face_recognition
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_rtsp_stream(self, connector_id: str, camera_id: str, rtsp_url: str):
    """
    Process RTSP stream for face detection
    Runs continuously in Celery worker

    Based on OpenCV VideoCapture documentation:
    https://docs.opencv.org/5.x/d8/dfe/classcv_1_1VideoCapture.html
    """
    logger.info(f"Starting RTSP stream processor for camera {camera_id}")

    # Open RTSP stream
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        logger.error(f"Failed to open RTSP stream: {rtsp_url}")
        return

    frame_count = 0
    process_every_n_frames = 30  # Process 1 frame per second at 30fps

    try:
        while cap.isOpened():
            ret, frame = cap.read()

            if not ret:
                logger.warning(f"Failed to read frame from camera {camera_id}")
                break

            frame_count += 1

            # Process every Nth frame to reduce load
            if frame_count % process_every_n_frames == 0:
                # Resize frame for faster processing
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                # Detect faces using face_recognition library
                face_locations = face_recognition.face_locations(rgb_frame, model="hog")

                if face_locations:
                    # Extract face encodings
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                    # Queue face recognition task
                    for face_encoding in face_encodings:
                        from .face_recognition_task import match_face_to_entity
                        match_face_to_entity.delay(
                            connector_id=connector_id,
                            camera_id=camera_id,
                            face_encoding=face_encoding.tolist(),
                            timestamp=datetime.now().isoformat()
                        )

            # Check if stream should be stopped (via Redis flag)
            if should_stop_stream(connector_id, camera_id):
                logger.info(f"Stopping RTSP stream for camera {camera_id}")
                break

    finally:
        cap.release()
        logger.info(f"RTSP stream processor stopped for camera {camera_id}")
```

---

### 3. Cisco/TP-Link Omada WiFi Connector

**Supported Controllers:** Cisco Meraki, Cisco WLC, TP-Link Omada SDN Controller
**Integration Method:** REST API

#### Implementation

```python
# backend/services/data_pipeline/connectors/wifi_connector.py

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
import httpx
from hashlib import sha256

from ..connector_base import BaseConnector, ConnectorConfig, ConnectorType, ConnectionMethod

logger = logging.getLogger(__name__)


class CiscoWiFiConnector(BaseConnector):
    """
    Pre-built connector for Cisco Wireless LAN Controllers

    Supported Systems:
    - Cisco Meraki Dashboard API
    - Cisco WLC (Catalyst 9800 series)
    - Cisco DNA Center

    Resources:
    - Meraki API: https://developer.cisco.com/meraki/
    - WLC Documentation: https://www.cisco.com/c/en/us/support/wireless/wireless-lan-controller-software/series.html
    - Community Forum: https://community.cisco.com/t5/wireless/wlc-rest-api/td-p/3029111

    Features:
    - Client tracking and history
    - AP association logs
    - Device location estimation
    - Client connectivity events
    """

    CONNECTOR_TYPE = ConnectorType.WIFI

    # Meraki API endpoints
    MERAKI_BASE_URL = "https://api.meraki.com/api/v1"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.http_client = None
        self.ap_location_map = {}

    async def initialize(self):
        """Initialize WiFi controller connection"""
        api_key = self.config.credentials.get('api_key')

        self.http_client = httpx.AsyncClient(
            base_url=self.config.endpoint or self.MERAKI_BASE_URL,
            headers={
                "X-Cisco-Meraki-API-Key": api_key,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

        # Load AP to location mapping
        self.ap_location_map = self.config.credentials.get('ap_mapping', {})

        logger.info(f"Cisco WiFi controller initialized: {self.config.endpoint}")

    async def test_connection(self) -> bool:
        """Test connection to Cisco WiFi controller"""
        try:
            # Test Meraki API
            org_id = self.config.credentials.get('organization_id')
            response = await self.http_client.get(f"/organizations/{org_id}")

            if response.status_code == 200:
                logger.info("Cisco Meraki API connection successful")
                return True

            return False
        except Exception as e:
            logger.error(f"Cisco WiFi connection test failed: {e}")
            return False

    async def fetch_data(self, since: datetime) -> List[Dict[str, Any]]:
        """
        Fetch WiFi client association events

        Cisco Meraki Dashboard API provides:
        - Client count history
        - Client connectivity events
        - Device location tracking
        """
        org_id = self.config.credentials.get('organization_id')
        network_id = self.config.credentials.get('network_id')

        # Fetch client history
        response = await self.http_client.get(
            f"/networks/{network_id}/wireless/clients/connectionStats",
            params={
                "t0": since.isoformat(),
                "t1": datetime.now().isoformat(),
                "perPage": 1000
            }
        )

        if response.status_code == 200:
            clients = response.json()
            return self._parse_client_events(clients)

        logger.error(f"Cisco API error: {response.status_code}")
        return []

    def _parse_client_events(self, clients: List[Dict]) -> List[Dict]:
        """Parse Cisco client data to Fazri format"""
        events = []

        for client in clients:
            try:
                # Hash MAC address for privacy
                mac_address = client.get('mac')
                device_hash = sha256(mac_address.encode()).hexdigest()[:16]

                # Parse connection events
                for connection in client.get('connectionStats', []):
                    events.append({
                        'device_hash': device_hash,
                        'device_mac': mac_address,  # Store for debugging, remove in prod
                        'ap_name': connection.get('apName'),
                        'ap_mac': connection.get('apMac'),
                        'location_id': self._map_ap_to_location(connection.get('apName')),
                        'timestamp': datetime.fromisoformat(connection.get('assoc')),
                        'signal_strength': connection.get('rssi', 0),
                        'event_type': 'wifi',
                        'source_dataset': 'wifi',
                        'raw_data': connection
                    })
            except Exception as e:
                logger.warning(f"Failed to parse client data: {e}")

        return events

    def _map_ap_to_location(self, ap_name: str) -> str:
        """Map access point to physical location"""
        return self.ap_location_map.get(ap_name, f"AP_{ap_name}")

    async def get_sample_data(self, n_records: int = 10) -> List[Dict[str, Any]]:
        """Get sample WiFi client data"""
        network_id = self.config.credentials.get('network_id')

        response = await self.http_client.get(
            f"/networks/{network_id}/clients",
            params={"perPage": n_records}
        )

        return response.json() if response.status_code == 200 else []

    async def close(self):
        """Clean up resources"""
        if self.http_client:
            await self.http_client.aclose()


class OmadaWiFiConnector(BaseConnector):
    """
    Pre-built connector for TP-Link Omada SDN Controllers

    Supported Systems:
    - TP-Link Omada Software Controller
    - TP-Link Omada Hardware Controller (OC200, OC300)
    - Omada Cloud-Based Controller

    Resources:
    - Omada Open API: https://use1-omada-northbound.tplinkcloud.com/doc.html/
    - Developer Documentation: Context7 Library ID /websites/use1-omada-northbound_tplinkcloud_doc
    - User Guide: https://www.tp-link.com/us/support/download/omada-software-controller/

    Authentication: OAuth 2.0 Client Credentials (access token valid 2 hours, refresh token 14 days)
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
            base_url=self.OMADA_BASE_URL,
            headers={
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

        logger.info(f"Omada Controller API initialized: {self.omadac_id}")

    async def _get_access_token(self):
        """
        Get OAuth 2.0 access token using Client Credentials Mode

        Token Details:
        - Access token valid for 2 hours (7200 seconds)
        - Refresh token valid for 14 days
        - Token becomes invalid if sites are copied/imported or permissions change
        """
        auth_client = httpx.AsyncClient(base_url=self.OMADA_BASE_URL)

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

            # Calculate token expiration time
            expires_in = result['expiresIn']  # 7200 seconds (2 hours)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # Refresh 5 min early

            logger.info("Omada access token obtained successfully")
        else:
            raise Exception(f"Failed to get Omada access token: {response.status_code} - {response.text}")

        await auth_client.aclose()

    async def _refresh_access_token(self):
        """Refresh access token using refresh token"""
        auth_client = httpx.AsyncClient(base_url=self.OMADA_BASE_URL)

        response = await auth_client.post(
            "/openapi/authorize/token",
            params={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            },
            json={
                "client_id": self.config.credentials['client_id'],
                "client_secret": self.config.credentials['client_secret']
            }
        )

        if response.status_code == 200:
            result = response.json()['result']
            self.access_token = result['accessToken']
            self.refresh_token = result['refreshToken']
            self.token_expires_at = datetime.now() + timedelta(seconds=result['expiresIn'] - 300)
            logger.info("Omada access token refreshed")
        else:
            # If refresh fails, get new token
            logger.warning("Token refresh failed, obtaining new token")
            await self._get_access_token()

        await auth_client.aclose()

    async def _ensure_valid_token(self):
        """Ensure access token is valid, refresh if needed"""
        if datetime.now() >= self.token_expires_at:
            await self._refresh_access_token()

    def _get_auth_header(self) -> Dict[str, str]:
        """Get authorization header with access token"""
        return {
            "Authorization": f"AccessToken={self.access_token}",
            "Content-Type": "application/json"
        }

    async def test_connection(self) -> bool:
        """Test Omada Controller API connection"""
        try:
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
        """
        Fetch wireless client connection events from Omada Controller

        Note: Omada Open API documentation doesn't explicitly show a client history endpoint.
        We'll use the audit logs for CLIENTS category to track connection events.
        """
        await self._ensure_valid_token()

        events = []

        try:
            # Fetch audit logs for client events
            # Omada tracks client connections in audit logs under CLIENTS category
            response = await self.http_client.get(
                f"/openapi/v1/{self.omadac_id}/sites/{self.site_id}/audit-logs",
                headers=self._get_auth_header(),
                params={
                    "category": "CLIENTS",
                    "startTime": int(since.timestamp() * 1000),  # Omada uses milliseconds
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
                # Extract client MAC address and connection details from log text
                log_text = log.get('text', '')

                # Omada logs typically include MAC address in the text
                # Example: "Client 00:11:22:33:44:55 connected to AP-Office-1"
                mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', log_text)

                if mac_match:
                    mac_address = mac_match.group(0)
                    device_hash = sha256(mac_address.encode()).hexdigest()[:16]

                    events.append({
                        'device_hash': device_hash,
                        'device_mac': mac_address,
                        'location_id': self.site_id,  # Can be enhanced with AP mapping
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

---

## Celery Worker Configuration

### Celery Application Setup

```python
# backend/services/data_pipeline/celery_app.py

from celery import Celery
from kombu import Queue, Exchange
import os

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

### Celery Configuration

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
}

# Result backend configuration
result_backend_transport_options = {
    'master_name': 'mymaster',
}

# Task serialization
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Priority queues configuration (Redis-specific)
# Note: Redis sorts priorities in REVERSE (0 is highest, 10 is lowest)
broker_transport_options = {
    'priority_steps': list(range(11)),  # 0-10 priority levels
    'sep': ':',
    'queue_order_strategy': 'priority',
}

# Queue definitions with priority
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
worker_max_tasks_per_child = 1000  # Restart worker after 1000 tasks (prevent memory leaks)
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
    'poll-essl-connectors': {
        'task': 'services.data_pipeline.tasks.connector_poller.poll_all_connectors',
        'schedule': 300.0,  # Every 5 minutes
        'options': {'queue': 'default', 'priority': 5}
    },
    'cleanup-old-results': {
        'task': 'services.data_pipeline.tasks.maintenance.cleanup_old_results',
        'schedule': 3600.0,  # Every hour
        'options': {'queue': 'default', 'priority': 1}
    },
}
```

### Starting Workers

```bash
# Start entity resolution workers (8 concurrent)
celery -A services.data_pipeline.celery_app worker \
    -Q entity_resolution \
    -c 8 \
    --loglevel=info \
    --hostname=entity@%h

# Start face recognition workers (4 concurrent, GPU-enabled)
celery -A services.data_pipeline.celery_app worker \
    -Q face_recognition \
    -c 4 \
    --loglevel=info \
    --hostname=face@%h

# Start graph building workers (4 concurrent)
celery -A services.data_pipeline.celery_app worker \
    -Q graph_building \
    -c 4 \
    --loglevel=info \
    --hostname=graph@%h

# Start anomaly detection workers (4 concurrent)
celery -A services.data_pipeline.celery_app worker \
    -Q anomaly_detection \
    -c 4 \
    --loglevel=info \
    --hostname=anomaly@%h

# Start beat scheduler (periodic tasks)
celery -A services.data_pipeline.celery_app beat \
    --loglevel=info
```

---

## Face Recognition Pipeline

### Face Recognition Task

```python
# backend/services/data_pipeline/tasks/face_recognition_task.py

from celery import shared_task
import face_recognition
import numpy as np
from typing import List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, name='face_recognition.match_face')
def match_face_to_entity(
    self,
    connector_id: str,
    camera_id: str,
    face_encoding: List[float],
    timestamp: str
) -> Optional[str]:
    """
    Match detected face to known entity using face_recognition library

    Based on face_recognition documentation:
    https://github.com/ageitgey/face_recognition

    Args:
        connector_id: Source connector ID
        camera_id: Camera that detected the face
        face_encoding: 128-dimensional face embedding
        timestamp: Detection timestamp

    Returns:
        entity_id if match found, None otherwise
    """
    try:
        # Convert list back to numpy array
        unknown_encoding = np.array(face_encoding)

        # Load known face encodings from database
        known_encodings, known_entity_ids = load_known_face_encodings()

        if not known_encodings:
            logger.warning("No known face encodings in database")
            return None

        # Compare unknown face against all known faces
        # Returns array of True/False
        matches = face_recognition.compare_faces(
            known_encodings,
            unknown_encoding,
            tolerance=0.6  # Lower = more strict (default 0.6)
        )

        # Calculate face distances (lower = better match)
        face_distances = face_recognition.face_distance(
            known_encodings,
            unknown_encoding
        )

        # Find best match
        if True in matches:
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index]:
                entity_id = known_entity_ids[best_match_index]
                confidence = 1 - face_distances[best_match_index]

                logger.info(
                    f"Face matched to entity {entity_id} "
                    f"with confidence {confidence:.2f}"
                )

                # Create CCTV event in database
                create_cctv_event(
                    entity_id=entity_id,
                    camera_id=camera_id,
                    timestamp=timestamp,
                    confidence=confidence,
                    connector_id=connector_id
                )

                return entity_id

        logger.info("No match found for detected face")
        return None

    except Exception as exc:
        logger.error(f"Face matching failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def load_known_face_encodings() -> tuple[List[np.ndarray], List[str]]:
    """
    Load all known face encodings from database

    Returns:
        (face_encodings, entity_ids)
    """
    from database import get_db_session

    session = get_db_session()

    # Query all entities with face encodings
    query = """
        SELECT entity_id, face_encoding
        FROM entities
        WHERE face_encoding IS NOT NULL
    """

    results = session.execute(query).fetchall()

    encodings = []
    entity_ids = []

    for row in results:
        # Face encodings stored as JSON array in DB
        encoding = np.array(row['face_encoding'])
        encodings.append(encoding)
        entity_ids.append(row['entity_id'])

    session.close()

    return encodings, entity_ids


def create_cctv_event(
    entity_id: str,
    camera_id: str,
    timestamp: str,
    confidence: float,
    connector_id: str
):
    """Create CCTV sighting event in database"""
    from database import get_db_session
    from services.graph_builder import get_graph_builder

    # Store in PostgreSQL
    session = get_db_session()

    event_data = {
        'entity_id': entity_id,
        'event_type': 'cctv_sighting',
        'location_id': camera_id,
        'timestamp': timestamp,
        'confidence': confidence,
        'source_connector': connector_id,
        'source_dataset': 'cctv'
    }

    # Insert into events table
    session.execute("""
        INSERT INTO events (entity_id, event_type, location_id, timestamp, confidence, source_dataset)
        VALUES (:entity_id, :event_type, :location_id, :timestamp, :confidence, :source_dataset)
    """, event_data)

    session.commit()
    session.close()

    # Queue graph building task
    from .graph_builder_task import create_graph_event
    create_graph_event.delay(event_data)


@shared_task(name='face_recognition.enroll_new_face')
def enroll_new_face(entity_id: str, face_image_path: str):
    """
    Enroll a new face for an entity

    Args:
        entity_id: Entity to enroll
        face_image_path: Path to face image
    """
    # Load image
    image = face_recognition.load_image_file(face_image_path)

    # Detect faces
    face_locations = face_recognition.face_locations(image)

    if not face_locations:
        logger.error(f"No face detected in image: {face_image_path}")
        return False

    if len(face_locations) > 1:
        logger.warning(f"Multiple faces detected, using first one")

    # Generate face encoding
    face_encodings = face_recognition.face_encodings(image, face_locations)
    face_encoding = face_encodings[0]

    # Store encoding in database
    from database import get_db_session
    session = get_db_session()

    session.execute("""
        UPDATE entities
        SET face_encoding = :encoding,
            updated_at = NOW()
        WHERE entity_id = :entity_id
    """, {
        'encoding': face_encoding.tolist(),
        'entity_id': entity_id
    })

    session.commit()
    session.close()

    logger.info(f"Face enrolled for entity {entity_id}")
    return True
```

---

## Implementation Roadmap

### Week 1-2: Foundation

**Goals:**
- Set up infrastructure
- Implement connector base classes
- Build schema detection ML model

**Tasks:**
1. [ ] Create database schema for connectors, quarantine, audit logs
2. [ ] Set up Redis + Celery worker infrastructure
3. [ ] Implement `BaseConnector` abstract class
4. [ ] Build `SchemaDetector` ML service
5. [ ] Create connector configuration models (Pydantic)
6. [ ] Write tests for base classes

**Deliverables:**
- Working connector framework
- Schema detection service
- Database migrations

---

### Week 3-4: Pre-built Connectors

**Goals:**
- Implement 3 critical connectors
- Build validation pipeline

**Tasks:**
1. [ ] Implement `ESSLCardReaderConnector`
   - Database polling method
   - API integration method
   - Field mapping logic
2. [ ] Implement `CPPlusCCTVConnector`
   - HTTP API integration
   - RTSP stream setup (basic)
   - Face detection event parsing
3. [ ] Implement `CiscoWiFiConnector` OR `OmadaWiFiConnector`
   - Testing with TP-Link Omada APs
   - OAuth 2.0 authentication (Client Credentials mode)
   - Client tracking via audit logs
4. [ ] Build `DataValidator` service
   - Schema validation
   - Data type checks
   - Referential integrity
   - Duplicate detection
5. [ ] Implement quarantine system
   - Database table for quarantine records
   - Admin review UI (basic)

**Deliverables:**
- 3 working pre-built connectors
- Validation & quarantine system
- Integration tests with mock data

---

### Week 5-6: Processing Pipeline & UI

**Goals:**
- Build end-to-end data flow
- Create admin configuration UI

**Tasks:**
1. [ ] Implement Celery tasks:
   - Entity resolution task
   - Graph building task
   - Face recognition task
   - Anomaly detection task
2. [ ] Build connector polling service
   - Periodic polling scheduler
   - Backoff on errors
   - Status monitoring
3. [ ] Create admin UI components:
   - Connector management page
   - Schema mapper interface (visual)
   - Quarantine review dashboard
   - Ingestion status monitoring
4. [ ] Implement RTSP stream processing
   - OpenCV video capture
   - Face detection integration
   - Frame sampling strategy
5. [ ] Build face enrollment UI
   - Upload face images
   - Assign to entities
   - Bulk enrollment

**Deliverables:**
- End-to-end ingestion pipeline
- Admin configuration UI
- Face recognition pipeline

---

### Week 7-8: Testing, Documentation & Deployment

**Goals:**
- Production readiness
- Comprehensive documentation
- Deployment automation

**Tasks:**
1. [ ] Integration testing:
   - Test with real hardware (eSSL, CP-PLUS, Cisco)
   - Test with mock data generators
   - Performance testing (100K events/day)
   - Error handling edge cases
2. [ ] Documentation:
   - Setup guide for each connector
   - Configuration examples
   - Troubleshooting guide
   - API documentation
3. [ ] Deployment automation:
   - Docker Compose for full stack
   - Kubernetes manifests (optional)
   - Environment-specific configs
   - Health check endpoints
4. [ ] Create demo environment:
   - Sample institution configuration
   - Mock data generators
   - Demo video recording
5. [ ] Training materials:
   - Video tutorials for in-house team
   - Step-by-step configuration guide
   - Common issues FAQ

**Deliverables:**
- Production-ready system
- Complete documentation
- Demo environment
- Training materials

---

## API Documentation & Resources

### Official Documentation Links

#### eSSL Card Readers
- [AmpleTrails eSSL API Documentation](https://ampletrails.com/essl-biometric-api/e-learning-blog)
- [eSSL Software Integration](https://www.esslsecurity.com/software-integration)
- [Cams Biometrics Protocol](https://camsbiometrics.com/product/cams-protocol-update-for-enabling-api-to-biometric-attendance-system.html)
- [eSSL Biometric Integration](https://essl.co.in/)

#### CP-PLUS CCTV
- [CP-PLUS AI NVR Products](https://www.cpplusworld.com/)
- [CP-PLUS Face Recognition Solution](https://www.cpplusworld.com/products/AIsuperprecisionsolution/Facerecognitionsolution)
- [iSpy CP-PLUS Setup Guide](https://www.ispyconnect.com/camera/cp-plus)
- ONVIF Protocol: Contact CP-PLUS support for SDK

#### Cisco WiFi Controllers
- [Cisco Meraki Developer Hub](https://developer.cisco.com/meraki/)
- [Meraki API - Client Tracking](https://developer.cisco.com/meraki/api-v1/get-organization-wireless-controller-clients-overview-history-by-device-by-interval/)
- [Cisco WLC Documentation](https://www.cisco.com/c/en/us/support/wireless/wireless-lan-controller-software/series.html)
- [WLC REST API Community Thread](https://community.cisco.com/t5/wireless/wlc-rest-api/td-p/3029111)

#### TP-Link Omada WiFi Controllers
- [Omada Open API Documentation](https://use1-omada-northbound.tplinkcloud.com/doc.html/)
- [Omada SDN Controller User Guide](https://www.tp-link.com/us/support/download/omada-software-controller/)
- Context7 Library: `/websites/use1-omada-northbound_tplinkcloud_doc`
- Authentication: OAuth 2.0 Client Credentials (2-hour token validity)

#### Open Source Libraries
- [Celery Documentation](https://docs.celeryq.dev/en/stable/)
- [OpenCV 5.x Documentation](https://docs.opencv.org/5.x/)
- [face_recognition Library](https://github.com/ageitgey/face_recognition)
- [Redis Documentation](https://redis.io/documentation)

---

## Next Steps

After reviewing this guide:

1. **Approve architecture** - Confirm the technical approach
2. **Prioritize connectors** - Which 3 connectors to build first?
3. **Set up development environment**:
   - Install Redis
   - Configure Celery
   - Set up GPU instance for face recognition
4. **Start Week 1 implementation** - Begin with connector base classes

---

**Document Version:** 1.0
**Last Updated:** March 6, 2026
**Maintained By:** Fazri Development Team
**Questions?** Refer to TODO.md or create issue in GitLab
