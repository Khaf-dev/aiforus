"""Geocoding (Nominatim) and walking routes (OSRM).

Limitations, stated plainly:

* The start point comes from IP geolocation (several km off). Routes are only
  meaningful once GPS from a phone is available (Fase 3).
* The public OSRM demo server only serves the car profile, so routes may use
  roads a pedestrian wouldn't. A self-hosted OSRM/GraphHopper with a foot
  profile fixes this.
* OSRM returns maneuvers, not sentences; :func:`describe_step` turns them
  into Indonesian/English instructions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import requests

from ..config import NavigationSettings
from ..hal.location import Location
from ..i18n import Translator

logger = logging.getLogger(__name__)


class NavigationError(Exception):
    def __init__(self, kind: str, detail: str = "") -> None:
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind = kind  # "network" | "not_found" | "no_route"


@dataclass(frozen=True)
class Place:
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RouteStep:
    maneuver: str  # OSRM maneuver type: depart, turn, arrive, roundabout, ...
    modifier: str | None  # left, slight right, straight, uturn, ...
    road: str
    distance_m: float
    exit: int | None = None


@dataclass
class Route:
    destination: str
    distance_m: float
    steps: list[RouteStep]


@dataclass
class NavigationSession:
    route: Route
    index: int = 0
    start: Location | None = None
    history: list[int] = field(default_factory=list)

    @property
    def current(self) -> RouteStep | None:
        return self.route.steps[self.index] if self.index < len(self.route.steps) else None

    @property
    def finished(self) -> bool:
        return self.index >= len(self.route.steps) - 1

    def advance(self) -> RouteStep | None:
        if self.index < len(self.route.steps) - 1:
            self.index += 1
            return self.current
        return None


def describe_step(step: RouteStep, tr: Translator) -> str:
    if step.maneuver == "arrive":
        road = tr.t("step_arrive_road", road=step.road) if step.road else ""
        return tr.t("step_arrive", road=road)
    if step.maneuver == "depart":
        maneuver = tr.t("maneuver_depart")
    elif step.maneuver in ("roundabout", "rotary", "roundabout turn") and step.exit:
        maneuver = tr.t("maneuver_roundabout", exit=step.exit)
    elif step.modifier and not (step.maneuver in ("continue", "new name") and step.modifier == "straight"):
        maneuver = tr.t("modifier_" + step.modifier.replace(" ", "_"))
    else:
        maneuver = tr.t("maneuver_continue")
    road = tr.t("step_road", road=step.road) if step.road else ""
    return tr.t("step_walk", maneuver=maneuver, road=road, distance=tr.distance(step.distance_m))


def parse_osrm_route(data: dict[str, Any], destination: str) -> Route:
    if data.get("code") != "Ok" or not data.get("routes"):
        raise NavigationError("no_route", str(data.get("code")))
    route = data["routes"][0]
    steps: list[RouteStep] = []
    for leg in route.get("legs", []):
        for raw in leg.get("steps", []):
            maneuver = raw.get("maneuver", {})
            steps.append(
                RouteStep(
                    maneuver=maneuver.get("type", "continue"),
                    modifier=maneuver.get("modifier"),
                    road=(raw.get("name") or "").strip(),
                    distance_m=float(raw.get("distance", 0.0)),
                    exit=maneuver.get("exit"),
                )
            )
    if not steps:
        raise NavigationError("no_route", "empty steps")
    return Route(destination=destination, distance_m=float(route.get("distance", 0.0)), steps=steps)


class Navigator:
    def __init__(self, settings: NavigationSettings, session: Any = None) -> None:
        self.settings = settings
        self._session = session or requests.Session()
        self._session.headers["User-Agent"] = settings.user_agent

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = self._session.get(url, params=params, timeout=self.settings.http_timeout_s)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise NavigationError("network", str(exc)) from exc

    def geocode(self, query: str, near: Location | None = None, language: str = "id") -> Place:
        params: dict[str, Any] = {"q": query, "format": "jsonv2", "limit": 1, "accept-language": language}
        if near is not None:  # bias (not restrict) results to the user's area
            d = 0.3
            params["viewbox"] = (
                f"{near.longitude - d},{near.latitude + d},{near.longitude + d},{near.latitude - d}"
            )
            params["bounded"] = 0
        results = self._get(self.settings.geocoding_url, params)
        if not results:
            raise NavigationError("not_found", query)
        top = results[0]
        name = top.get("name") or str(top.get("display_name", query)).split(",")[0]
        return Place(name=name, latitude=float(top["lat"]), longitude=float(top["lon"]))

    def route(self, start: Location, destination: Place) -> Route:
        base = self.settings.routing_url.rstrip("/")
        coords = f"{start.longitude},{start.latitude};{destination.longitude},{destination.latitude}"
        url = f"{base}/route/v1/{self.settings.routing_profile}/{coords}"
        data = self._get(url, {"steps": "true", "overview": "false", "alternatives": "false"})
        return parse_osrm_route(data, destination.name)

    def walking_minutes(self, route: Route) -> int:
        return max(1, round(route.distance_m / self.settings.walking_speed_mps / 60))
