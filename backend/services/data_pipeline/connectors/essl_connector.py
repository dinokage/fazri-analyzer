# backend/services/data_pipeline/connectors/essl_connector.py
"""
eSSL Card Reader Connector

Supports eSSL card reader systems including:
- X990 series
- K90 series
- K30 Pro series
- F22 series

Connection methods:
- DATABASE: Direct MySQL database connection
- REST_API: HTTP API endpoints
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from backend.services.data_pipeline.connector_base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorType,
    ConnectionMethod
)

logger = logging.getLogger(__name__)


class ESSLCardReaderConnector(BaseConnector):
    """Connector for eSSL card reader systems."""

    CONNECTOR_TYPE = ConnectorType.CARD_SWIPE

    # Database schema for eSSL systems
    DB_SCHEMA = {
        "table": "AccessLogs",
        "fields": ["UserID", "CardNo", "AccessTime", "DoorID", "InOutStatus", "DeviceID"]
    }

    def __init__(self, config: ConnectorConfig) -> None:
        """Initialize eSSL connector."""
        super().__init__(config)
        self.db_pool = None
        self.http_client = None

    async def initialize(self) -> None:
        """Initialize connections based on connection method."""
        if self.config.connection_method == ConnectionMethod.DATABASE:
            await self._init_database()
        elif self.config.connection_method == ConnectionMethod.REST_API:
            await self._init_http_client()
        else:
            raise ValueError(f"Unsupported connection method: {self.config.connection_method}")

    async def _init_database(self) -> None:
        """Initialize MySQL database connection pool."""
        try:
            import aiomysql

            self.db_pool = await aiomysql.create_pool(
                host=self.config.credentials.get("host", "localhost"),
                port=int(self.config.credentials.get("port", 3306)),
                user=self.config.credentials.get("username"),
                password=self.config.credentials.get("password"),
                db=self.config.credentials.get("database"),
                autocommit=True,
                minsize=1,
                maxsize=5
            )
            self.logger.info("Database connection pool initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise

    async def _init_http_client(self) -> None:
        """Initialize HTTP client for REST API."""
        try:
            import httpx

            self.http_client = httpx.AsyncClient(
                base_url=self.config.endpoint,
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.config.credentials.get('api_key', '')}",
                    "Content-Type": "application/json"
                }
            )
            self.logger.info("HTTP client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize HTTP client: {e}")
            raise

    async def test_connection(self) -> bool:
        """Test connection to eSSL data source."""
        try:
            if self.config.connection_method == ConnectionMethod.DATABASE:
                return await self._test_database_connection()
            elif self.config.connection_method == ConnectionMethod.REST_API:
                return await self._test_api_connection()
            return False
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    async def _test_database_connection(self) -> bool:
        """Test MySQL database connection."""
        if not self.db_pool:
            await self._init_database()

        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    return result is not None
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            return False

    async def _test_api_connection(self) -> bool:
        """Test REST API connection."""
        if not self.http_client:
            await self._init_http_client()

        try:
            response = await self.http_client.get("/health")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"API connection test failed: {e}")
            return False

    async def fetch_data(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch card swipe data since last sync."""
        if self.config.connection_method == ConnectionMethod.DATABASE:
            return await self._fetch_from_database(since)
        elif self.config.connection_method == ConnectionMethod.REST_API:
            return await self._fetch_from_api(since)
        return []

    async def _fetch_from_database(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch data from MySQL database."""
        if not self.db_pool:
            await self._init_database()

        import aiomysql

        table_name = self.config.credentials.get("table_name", self.DB_SCHEMA["table"])

        # Build query - limit to 5000 records for safety
        query = f"""
            SELECT * FROM {table_name}
            WHERE AccessTime > %s
            ORDER BY AccessTime ASC
            LIMIT 5000
        """

        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, (since,))
                    results = await cursor.fetchall()
                    self.logger.info(f"Fetched {len(results)} records from database")
                    return list(results)
        except Exception as e:
            self.logger.error(f"Failed to fetch data from database: {e}")
            return []

    async def _fetch_from_api(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch data from REST API."""
        if not self.http_client:
            await self._init_http_client()

        try:
            response = await self.http_client.get(
                "/access-logs",
                params={
                    "since": since.isoformat(),
                    "limit": 5000
                }
            )
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Fetched {len(data)} records from API")
            return data
        except Exception as e:
            self.logger.error(f"Failed to fetch data from API: {e}")
            return []

    async def get_sample_data(self, n_records: int = 10) -> List[Dict[str, Any]]:
        """Get sample data for schema detection."""
        if self.config.connection_method == ConnectionMethod.DATABASE:
            return await self._get_sample_from_database(n_records)
        elif self.config.connection_method == ConnectionMethod.REST_API:
            return await self._get_sample_from_api(n_records)
        return []

    async def _get_sample_from_database(self, n_records: int) -> List[Dict[str, Any]]:
        """Get sample data from database."""
        if not self.db_pool:
            await self._init_database()

        import aiomysql

        table_name = self.config.credentials.get("table_name", self.DB_SCHEMA["table"])
        query = f"SELECT * FROM {table_name} ORDER BY AccessTime DESC LIMIT %s"

        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, (n_records,))
                    results = await cursor.fetchall()
                    return list(results)
        except Exception as e:
            self.logger.error(f"Failed to get sample data: {e}")
            return []

    async def _get_sample_from_api(self, n_records: int) -> List[Dict[str, Any]]:
        """Get sample data from API."""
        if not self.http_client:
            await self._init_http_client()

        try:
            response = await self.http_client.get(
                "/access-logs/sample",
                params={"limit": n_records}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to get sample data from API: {e}")
            return []

    def normalize_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize eSSL data to Fazri format with timestamp parsing.

        Applies field mappings and parses timestamps to datetime objects.
        Adds metadata fields for tracking.
        """
        normalized = []

        for record in raw_data:
            try:
                # Apply field mappings
                mapped_record = {}
                for source_field, fazri_field in self.config.field_mapping.items():
                    if source_field in record:
                        value = record[source_field]

                        # Parse timestamps
                        if fazri_field == "timestamp" and isinstance(value, str):
                            value = self._parse_timestamp(value)

                        mapped_record[fazri_field] = value

                # Add metadata
                mapped_record["source_dataset"] = self.config.connector_id
                mapped_record["source_connector"] = "essl_card_reader"
                mapped_record["event_type"] = "card_swipe"

                normalized.append(mapped_record)

            except Exception as e:
                self.logger.warning(f"Failed to normalize record: {e}, Record: {record}")
                continue

        return normalized

    def _parse_timestamp(self, value: str) -> datetime:
        """
        Parse timestamp from various eSSL formats.

        Supported formats:
        - 2026-03-06 14:30:45 (standard)
        - 06/03/2026 14:30:45 (alternate)
        - 2026-03-06T14:30:45 (ISO format)
        """
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        # If all formats fail, raise error with helpful message
        raise ValueError(
            f"Unable to parse timestamp '{value}'. "
            f"Supported formats: {', '.join(formats)}"
        )

    async def close(self) -> None:
        """Clean up resources."""
        if self.db_pool:
            self.db_pool.close()
            await self.db_pool.wait_closed()
            self.logger.info("Database connection pool closed")

        if self.http_client:
            await self.http_client.aclose()
            self.logger.info("HTTP client closed")
