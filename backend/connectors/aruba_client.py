"""
Aruba AOS8 REST API connector for WiFi device association events.

Polls the Aruba controller for currently associated clients, compares
against the previous poll to detect movements (device switches AP = zone
change), and returns SensorEvents.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from config import settings
from models.schemas.sensor_events import EventType, SensorEvent, SensorType

logger = logging.getLogger(__name__)

# WiFi confidence — lower than RFID because AP coverage areas overlap
_WIFI_CONFIDENCE = 0.85


class ArubaAOS8Client:
    """
    Polls Aruba AOS8 REST API for associated WiFi clients.

    Parameters
    ----------
    base_url:
        Root URL of the Aruba controller, e.g. http://10.0.0.1:4343
    username / password:
        Admin credentials.
    ap_zone_map:
        Maps Aruba AP names to FAZRI zone_ids.
        e.g. {"AP-LIB-1F-01": "LIB_ENT", "AP-CAF-1F-01": "CAF_01"}
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        ap_zone_map: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self.ap_zone_map: Dict[str, str] = ap_zone_map or {}
        self._token: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def login(self) -> str:
        """Authenticate and store the session token.  Returns the token."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/v1/api/login",
                params={"username": self._username, "password": self._password},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["GlobalResult"]["UIDARUBA"]
            logger.debug("Aruba login OK — token obtained")
            return self._token

    async def get_associated_clients(self) -> List[SensorEvent]:
        """
        Fetch currently associated clients and normalise to SensorEvents.

        Re-logins automatically on 401.
        """
        token = await self._ensure_token()
        raw_clients = await self._fetch_clients(token)
        return [
            ev
            for raw in raw_clients
            for ev in [self._client_to_event(raw)]
            if ev is not None
        ]

    async def detect_movements(
        self,
        previous: List[SensorEvent],
        current: List[SensorEvent],
    ) -> List[SensorEvent]:
        """
        Diff previous vs current client list to generate movement events.

        For each MAC:
        - Appeared on a new AP since last poll → DEVICE_ASSOCIATED event
        - No longer seen → DEVICE_DISASSOCIATED event
        - Same AP → no event (stable, no movement)
        """
        prev_by_mac: Dict[str, str] = {e.raw_identifier: e.zone_id for e in previous}
        curr_by_mac: Dict[str, str] = {e.raw_identifier: e.zone_id for e in current}

        events: List[SensorEvent] = []
        now = datetime.now(timezone.utc)

        # Devices that moved (same MAC, different zone)
        for mac, curr_zone in curr_by_mac.items():
            prev_zone = prev_by_mac.get(mac)
            if prev_zone is None:
                # New association
                events.append(
                    SensorEvent(
                        sensor_type=SensorType.WIFI,
                        event_type=EventType.DEVICE_ASSOCIATED,
                        timestamp=now,
                        zone_id=curr_zone,
                        raw_identifier=mac,
                        identifier_type="mac_address",
                        confidence=_WIFI_CONFIDENCE,
                        metadata={"movement": "new_association"},
                    )
                )
            elif prev_zone != curr_zone:
                # Movement to a different zone
                events.append(
                    SensorEvent(
                        sensor_type=SensorType.WIFI,
                        event_type=EventType.DEVICE_ASSOCIATED,
                        timestamp=now,
                        zone_id=curr_zone,
                        raw_identifier=mac,
                        identifier_type="mac_address",
                        confidence=_WIFI_CONFIDENCE,
                        metadata={"movement": "zone_change", "from_zone": prev_zone},
                    )
                )

        # Devices that left
        for mac, prev_zone in prev_by_mac.items():
            if mac not in curr_by_mac:
                events.append(
                    SensorEvent(
                        sensor_type=SensorType.WIFI,
                        event_type=EventType.DEVICE_DISASSOCIATED,
                        timestamp=now,
                        zone_id=prev_zone,
                        raw_identifier=mac,
                        identifier_type="mac_address",
                        confidence=_WIFI_CONFIDENCE,
                        metadata={"movement": "disassociated"},
                    )
                )

        return events

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_token(self) -> str:
        if self._token is None:
            return await self.login()
        return self._token

    async def _fetch_clients(self, token: str) -> List[dict]:
        """GET /v1/monitoring/client — re-login on 401."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/v1/monitoring/client",
                params={"UIDARUBA": token},
                cookies={"UIDARUBA": token},
            )
            if resp.status_code == 401:
                logger.info("Aruba token expired — re-logging in")
                self._token = None
                token = await self.login()
                resp = await client.get(
                    f"{self.base_url}/v1/monitoring/client",
                    params={"UIDARUBA": token},
                    cookies={"UIDARUBA": token},
                )
            resp.raise_for_status()
            return resp.json().get("Clients", [])

    def _client_to_event(self, raw: dict) -> Optional[SensorEvent]:
        """Normalise an Aruba client dict to a SensorEvent."""
        try:
            mac = (raw.get("MAC") or "").strip().lower()
            if not mac:
                return None

            ap_name = raw.get("AP name", "")
            zone_id = self.ap_zone_map.get(ap_name, f"AP_{ap_name}")

            assoc_time_str = raw.get("Association Time", "")
            try:
                ts = datetime.fromisoformat(assoc_time_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                ts = datetime.now(timezone.utc)

            return SensorEvent(
                sensor_type=SensorType.WIFI,
                event_type=EventType.DEVICE_ASSOCIATED,
                timestamp=ts,
                zone_id=zone_id,
                raw_identifier=mac,
                identifier_type="mac_address",
                confidence=_WIFI_CONFIDENCE,
                source_device_id=ap_name,
                raw_payload={
                    "MAC": mac,
                    "AP name": ap_name,
                    "ESSID": raw.get("ESSID"),
                    "Signal": raw.get("Signal"),
                    "Role": raw.get("Role"),
                    "Status": raw.get("Status"),
                },
            )
        except Exception as exc:
            logger.debug("Skipping malformed Aruba client record: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_aruba_client: Optional[ArubaAOS8Client] = None


def get_aruba_client() -> ArubaAOS8Client:
    """Return the process-level ArubaAOS8Client singleton."""
    global _aruba_client
    if _aruba_client is None:
        ap_zone_map: Dict[str, str] = {}
        try:
            ap_zone_map = json.loads(settings.ARUBA_AP_ZONE_MAP)
        except Exception:
            pass

        _aruba_client = ArubaAOS8Client(
            base_url=settings.ARUBA_BASE_URL,
            username=settings.ARUBA_USERNAME,
            password=settings.ARUBA_PASSWORD,
            ap_zone_map=ap_zone_map,
        )
    return _aruba_client
