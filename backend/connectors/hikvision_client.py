"""
Hikvision ISAPI access control event connector.

Polls the Hikvision NVR/access controller for AcsEvents and normalises them
to the internal SensorEvent schema.

Works against both real hardware and the Hikvision simulator
(backend/simulators/hikvision_simulator.py).
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
from httpx import DigestAuth

from config import settings
from models.schemas.sensor_events import EventType, SensorEvent, SensorType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hikvision ISAPI XML templates
# ---------------------------------------------------------------------------

_SEARCH_BODY = """<?xml version="1.0" encoding="UTF-8" ?>
<AcsEventSearchCond xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <searchID>{search_id}</searchID>
  <searchResultPosition>{position}</searchResultPosition>
  <maxResults>{max_results}</maxResults>
  <major>0</major>
  <minor>0</minor>
  <startTime>{start_time}</startTime>
  <endTime>{end_time}</endTime>
</AcsEventSearchCond>
"""

_HIKVISION_NS = {"h": "http://www.hikvision.com/ver20/XMLSchema"}


def _find_text(el: ET.Element, tag: str) -> Optional[str]:
    """Find a child element's text, trying both namespaced and bare forms."""
    child = el.find(f"h:{tag}", _HIKVISION_NS)
    if child is None:
        child = el.find(tag)
    return child.text if child is not None else None


# ---------------------------------------------------------------------------
# Event minor code → EventType mapping
# ---------------------------------------------------------------------------

_MINOR_TO_EVENT_TYPE: Dict[str, EventType] = {
    "1": EventType.ACCESS_GRANTED,
    "38": EventType.ACCESS_DENIED,
    "75": EventType.ACCESS_DENIED,  # Anti-passback
}


class HikvisionISAPIClient:
    """
    Polls the Hikvision ISAPI /ISAPI/AccessControl/AcsEvent/search endpoint.

    Parameters
    ----------
    base_url:
        Root URL of the NVR or access controller, e.g. http://192.168.1.64
    username / password:
        Admin credentials.  Uses HTTP Digest authentication.
    door_zone_map:
        Maps Hikvision door numbers (str) to FAZRI zone_ids.
        e.g. {"1": "LIB_ENT", "2": "LAB_101"}
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        door_zone_map: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._auth = DigestAuth(username, password)
        self.door_zone_map: Dict[str, str] = door_zone_map or {}
        self._device_serial: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def poll_access_events(
        self,
        since: datetime,
        max_results: int = 50,
    ) -> List[SensorEvent]:
        """
        Fetch AcsEvents that occurred after ``since`` and return them as
        normalised SensorEvents.

        Handles pagination automatically (responseStatusStrg == "MORE").
        Retries with exponential backoff on connection errors (3 attempts).
        """
        if self._device_serial is None:
            await self._fetch_device_info()

        events: List[SensorEvent] = []
        position = 0
        search_id = f"fazri-{int(since.timestamp())}"
        now = datetime.now(timezone.utc)

        async with httpx.AsyncClient(auth=self._auth, timeout=10) as client:
            while True:
                body = _SEARCH_BODY.format(
                    search_id=search_id,
                    position=position,
                    max_results=max_results,
                    start_time=since.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    end_time=now.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                )

                resp = await self._post_with_retry(
                    client,
                    f"{self.base_url}/ISAPI/AccessControl/AcsEvent/search",
                    content=body,
                    content_type="application/xml",
                )

                batch, more = self._parse_events(resp.text)
                events.extend(batch)
                position += len(batch)

                if not more or not batch:
                    break

        logger.debug("Hikvision poll: fetched %d events since %s", len(events), since)
        return events

    async def get_device_info(self) -> dict:
        """Health check — returns parsed device info."""
        return await self._fetch_device_info()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_device_info(self) -> dict:
        async with httpx.AsyncClient(auth=self._auth, timeout=5) as client:
            resp = await self._post_with_retry(
                client,
                f"{self.base_url}/ISAPI/System/deviceInfo",
                content="",
                content_type="application/xml",
            )
        try:
            root = ET.fromstring(resp.text)
            info = {
                "serial": _find_text(root, "serialNumber") or "unknown",
                "model": _find_text(root, "model") or "unknown",
                "firmware": _find_text(root, "firmwareVersion") or "unknown",
            }
            self._device_serial = info["serial"]
            return info
        except Exception as exc:
            logger.warning("Failed to parse device info: %s", exc)
            return {}

    async def _post_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        content: str,
        content_type: str,
        max_retries: int = 3,
    ) -> httpx.Response:
        """POST with exponential backoff on connection errors."""
        import asyncio

        delay = 2
        for attempt in range(max_retries):
            try:
                resp = await client.post(
                    url,
                    content=content.encode(),
                    headers={"Content-Type": content_type},
                )
                resp.raise_for_status()
                return resp
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    "Hikvision connection error (attempt %d/%d): %s — retrying in %ds",
                    attempt + 1, max_retries, exc, delay,
                )
                await asyncio.sleep(delay)
                delay *= 2
        raise RuntimeError("Exhausted retries")  # never reached

    def _parse_events(self, xml_text: str) -> tuple[List[SensorEvent], bool]:
        """Parse XML response → (list of SensorEvents, has_more)."""
        events: List[SensorEvent] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("Failed to parse Hikvision XML: %s", exc)
            return events, False

        status_str = (
            _find_text(root, "responseStatusStrg") or ""
        ).upper()
        has_more = status_str == "MORE"

        info_el = root.find("h:AcsEventInfo", _HIKVISION_NS)
        if info_el is None:
            info_el = root.find("AcsEventInfo")
        if info_el is None:
            return events, has_more

        acs_events = info_el.findall("h:AcsEvent", _HIKVISION_NS)
        if not acs_events:
            acs_events = info_el.findall("AcsEvent")
        for acs_ev in acs_events:
            ev = self._parse_single_event(acs_ev)
            if ev is not None:
                events.append(ev)

        return events, has_more

    def _parse_single_event(self, el: ET.Element) -> Optional[SensorEvent]:
        """Normalise a single AcsEvent XML element into a SensorEvent."""
        try:
            card_no = _find_text(el, "cardNo") or ""
            if not card_no:
                return None

            raw_ts = _find_text(el, "dateTime") or ""
            try:
                ts = datetime.fromisoformat(raw_ts)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                ts = datetime.now(timezone.utc)

            minor = _find_text(el, "minor") or "1"
            event_type = _MINOR_TO_EVENT_TYPE.get(minor, EventType.ACCESS_GRANTED)

            door_no = _find_text(el, "doorNo") or "1"
            zone_id = self.door_zone_map.get(door_no, f"DOOR_{door_no}")

            return SensorEvent(
                sensor_type=SensorType.RFID,
                event_type=event_type,
                timestamp=ts,
                zone_id=zone_id,
                raw_identifier=card_no,
                identifier_type="card_id",
                confidence=1.0,
                source_device_id=self._device_serial,
                raw_payload={
                    "dateTime": raw_ts,
                    "employeeNo": _find_text(el, "employeeNoString"),
                    "cardNo": card_no,
                    "name": _find_text(el, "name"),
                    "doorNo": door_no,
                    "minor": minor,
                    "verifyMode": _find_text(el, "currentVerifyMode"),
                },
            )
        except Exception as exc:
            logger.debug("Skipping malformed AcsEvent: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_hikvision_client: Optional[HikvisionISAPIClient] = None


def get_hikvision_client() -> HikvisionISAPIClient:
    """Return the process-level HikvisionISAPIClient singleton."""
    global _hikvision_client
    if _hikvision_client is None:
        door_zone_map: Dict[str, str] = {}
        try:
            door_zone_map = json.loads(settings.HIKVISION_DOOR_ZONE_MAP)
        except Exception as e:
            logger.warning(
                "Failed to parse HIKVISION_DOOR_ZONE_MAP JSON: %s | value: %r",
                e, settings.HIKVISION_DOOR_ZONE_MAP,
            )

        _hikvision_client = HikvisionISAPIClient(
            base_url=settings.HIKVISION_BASE_URL,
            username=settings.HIKVISION_USERNAME,
            password=settings.HIKVISION_PASSWORD,
            door_zone_map=door_zone_map,
        )
    return _hikvision_client
