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
