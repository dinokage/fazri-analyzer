# backend/services/data_pipeline/connectors/omada_connector.py
"""
TP-Link Omada WiFi Connector

Supports TP-Link Omada SDN Controllers with OAuth 2.0 authentication.
Extracts WiFi client connection events from audit logs.

Connection methods:
- REST_API: Omada Northbound API with OAuth 2.0
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
import logging
import re
import hashlib
import httpx

from backend.services.data_pipeline.connector_base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorType,
    ConnectionMethod
)

logger = logging.getLogger(__name__)


class OmadaWiFiConnector(BaseConnector):
    """Connector for TP-Link Omada WiFi controllers."""

    CONNECTOR_TYPE = ConnectorType.WIFI
    OMADA_BASE_URL = "https://use1-omada-northbound.tplinkcloud.com"

    # OAuth token validity (2 hours, refresh 5 minutes early)
    TOKEN_VALIDITY_SECONDS = 7200
    TOKEN_REFRESH_MARGIN_SECONDS = 300

    # MAC address regex pattern
    MAC_PATTERN = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')

    def __init__(self, config: ConnectorConfig) -> None:
        """Initialize Omada WiFi connector."""
        super().__init__(config)
        self._validate_config()
        self.http_client: Optional[httpx.AsyncClient] = None
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

    def _validate_config(self) -> None:
        """Validate configuration has required credentials."""
        required = ["omadac_id", "client_id", "client_secret", "site_id"]
        missing = [key for key in required if key not in self.config.credentials]
        if missing:
            raise ValueError(f"Missing required credentials: {', '.join(missing)}")

        if self.config.connection_method != ConnectionMethod.REST_API:
            raise ValueError("Omada connector only supports REST_API connection method")

    async def initialize(self) -> None:
        """Initialize HTTP client and authenticate."""
        logger.info(f"Initializing Omada WiFi connector: {self.config.connector_id}")

        # Use custom endpoint if provided, otherwise use default
        base_url = self.config.endpoint or self.OMADA_BASE_URL

        self.http_client = httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"}
        )

        # Get initial OAuth token
        await self._get_access_token()
        logger.info(f"Omada connector initialized successfully: {self.config.connector_id}")

    async def _get_access_token(self) -> None:
        """
        Obtain OAuth 2.0 access token using Client Credentials flow.

        Token is valid for 2 hours (7200 seconds).
        """
        logger.info("Requesting OAuth 2.0 access token from Omada API")

        token_url = f"/openapi/authorize/token?grant_type=client_credentials"

        try:
            response = await self.http_client.post(
                token_url,
                auth=(
                    self.config.credentials["client_id"],
                    self.config.credentials["client_secret"]
                )
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get("accessToken")
            expires_in = token_data.get("expiresIn", self.TOKEN_VALIDITY_SECONDS)

            # Calculate expiration time
            self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            logger.info(f"OAuth token obtained, expires at: {self.token_expires_at}")

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get OAuth token: {e.response.status_code} - {e.response.text}")
            raise ConnectionError(f"OAuth authentication failed: {e}")
        except Exception as e:
            logger.error(f"Error during OAuth token request: {e}")
            raise

    async def _ensure_valid_token(self) -> None:
        """Ensure the access token is valid, refresh if needed."""
        if not self.access_token or not self.token_expires_at:
            await self._get_access_token()
            return

        # Refresh if token expires within 5 minutes
        time_until_expiry = (self.token_expires_at - datetime.now(timezone.utc)).total_seconds()
        if time_until_expiry < self.TOKEN_REFRESH_MARGIN_SECONDS:
            logger.info("Access token expiring soon, refreshing...")
            await self._get_access_token()

    def _get_auth_header(self) -> Dict[str, str]:
        """Get authorization header with current access token."""
        if not self.access_token:
            raise ValueError("No access token available. Call initialize() first.")
        return {"Authorization": f"AccessToken={self.access_token}"}

    async def test_connection(self) -> bool:
        """Test API connectivity."""
        try:
            await self._ensure_valid_token()

            # Test by fetching site info
            omadac_id = self.config.credentials["omadac_id"]
            site_id = self.config.credentials["site_id"]
            url = f"/openapi/v1/{omadac_id}/sites/{site_id}"

            response = await self.http_client.get(
                url,
                headers=self._get_auth_header()
            )
            response.raise_for_status()

            logger.info("Omada API connection test successful")
            return True

        except Exception as e:
            logger.error(f"Omada API connection test failed: {e}")
            return False

    async def fetch_data(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch WiFi client events from audit logs.

        Args:
            since: Fetch logs after this timestamp (default: last 24 hours)

        Returns:
            List of normalized WiFi events with device hashes
        """
        await self._ensure_valid_token()

        # Default to last 24 hours if no timestamp provided
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=24)

        # Convert to milliseconds for Omada API
        start_timestamp = int(since.timestamp() * 1000)
        end_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)

        logger.info(f"Fetching Omada audit logs from {since} to now")

        omadac_id = self.config.credentials["omadac_id"]
        site_id = self.config.credentials["site_id"]

        all_logs = []
        page = 1
        page_size = 1000  # Max page size for Omada API

        try:
            while True:
                url = f"/openapi/v1/{omadac_id}/sites/{site_id}/audit-logs"
                params = {
                    "page": page,
                    "pageSize": page_size,
                    "startTime": start_timestamp,
                    "endTime": end_timestamp,
                    "category": "CLIENTS"  # Filter for client events
                }

                response = await self.http_client.get(
                    url,
                    params=params,
                    headers=self._get_auth_header()
                )
                response.raise_for_status()

                data = response.json()
                logs = data.get("data", [])

                if not logs:
                    break

                all_logs.extend(logs)

                # Check if there are more pages
                total_rows = data.get("totalRows", 0)
                if len(all_logs) >= total_rows:
                    break

                page += 1
                logger.debug(f"Fetched page {page-1}, total logs: {len(all_logs)}/{total_rows}")

            logger.info(f"Fetched {len(all_logs)} audit log entries")

            # Parse logs into events
            events = self._parse_client_logs(all_logs)
            logger.info(f"Parsed {len(events)} WiFi client events")

            return events

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch audit logs: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error fetching Omada data: {e}")
            raise

    def _parse_client_logs(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse audit logs and extract WiFi client events.

        Extracts MAC addresses from log text and creates normalized events.
        MAC addresses are hashed for privacy (SHA256, first 16 chars).

        Args:
            logs: Raw audit log entries

        Returns:
            List of normalized WiFi events
        """
        events = []

        for log in logs:
            # Extract MAC address from log text
            log_text = log.get("text", "")
            mac_match = self.MAC_PATTERN.search(log_text)

            if not mac_match:
                continue  # Skip logs without MAC addresses

            mac_address = mac_match.group(0).upper()

            # Hash MAC address for privacy (GDPR compliance)
            device_hash = hashlib.sha256(mac_address.encode()).hexdigest()[:16]

            # Convert timestamp from milliseconds to datetime
            timestamp_ms = log.get("timestamp", 0)
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000)

            # Extract location info (AP name, site, etc.)
            site = log.get("site", "unknown")

            # Try to extract AP name from log text
            ap_match = re.search(r'to (AP-[\w-]+)', log_text)
            location_id = ap_match.group(1) if ap_match else site

            event = {
                "device_hash": device_hash,
                # device_mac removed for privacy/GDPR compliance
                "location_id": location_id,
                "timestamp": timestamp,
                "event_type": "wifi",
                "source_dataset": f"omada_{self.config.connector_id}",
                "metadata": {
                    "site": site,
                    "controller": log.get("controller"),
                    "log_text": log_text,
                    "category": log.get("category")
                }
            }

            events.append(event)

        return events

    async def get_sample_data(self, n_records: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch a small sample of recent data for testing.

        Args:
            n_records: Number of records to fetch

        Returns:
            Sample of recent WiFi events
        """
        if n_records <= 0:
            raise ValueError(f"n_records must be positive, got {n_records}")
        if n_records > 10000:
            raise ValueError(f"n_records too large (max 10000), got {n_records}")

        logger.info(f"Fetching sample data: {n_records} records")

        # Fetch last hour of data
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        events = await self.fetch_data(since=since)

        # Return up to n_records
        return events[:n_records]

    async def close(self) -> None:
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

        self.access_token = None
        self.token_expires_at = None

        logger.info(f"Omada connector closed: {self.config.connector_id}")
