"""Location providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    label: str
    accuracy_m: float
    source: str

    @property
    def is_approximate(self) -> bool:
        # Anything worse than ~50 m is useless for walking directions.
        return self.accuracy_m > 50


class LocationProvider(Protocol):
    def locate(self) -> Location | None:
        """Blocking. None if the location can't be determined."""


class IpLocationProvider:
    """City-level location from the public IP address (ipinfo.io).

    Accuracy is typically several kilometres; it exists so the assistant can
    say *roughly* where the user is. Real walking navigation needs GPS from
    a phone (Fase 3).
    """

    ACCURACY_M = 5000.0

    def __init__(self, url: str, timeout_s: float, user_agent: str, session: Any = None) -> None:
        import requests

        self._url = url
        self._timeout_s = timeout_s
        self._session = session or requests.Session()
        self._session.headers.setdefault("User-Agent", user_agent)

    def locate(self) -> Location | None:
        try:
            response = self._session.get(self._url, timeout=self._timeout_s)
            response.raise_for_status()
            data = response.json()
            lat_str, lon_str = str(data["loc"]).split(",")
            parts = [data.get("city"), data.get("region"), data.get("country")]
            label = ", ".join(p for p in parts if p)
            return Location(float(lat_str), float(lon_str), label, self.ACCURACY_M, "ip")
        except Exception as exc:  # network, HTTP, malformed JSON
            logger.warning("IP geolocation failed: %s", exc)
            return None
