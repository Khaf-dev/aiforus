import pytest
import requests

from aiforus.config import NavigationSettings
from aiforus.hal.location import Location
from aiforus.i18n import Translator
from aiforus.services.navigation import (
    NavigationError,
    NavigationSession,
    Navigator,
    Place,
    RouteStep,
    describe_step,
    parse_osrm_route,
)

OSRM_SAMPLE = {
    "code": "Ok",
    "routes": [
        {
            "distance": 1234.5,
            "duration": 200,
            "legs": [
                {
                    "steps": [
                        {"name": "Jalan Kebon Sirih", "distance": 120.4, "maneuver": {"type": "depart"}},
                        {
                            "name": "Jalan Medan Merdeka Selatan",
                            "distance": 640,
                            "maneuver": {"type": "turn", "modifier": "left"},
                        },
                        {
                            "name": "",
                            "distance": 300,
                            "maneuver": {"type": "roundabout", "modifier": "right", "exit": 2},
                        },
                        {
                            "name": "Jalan Thamrin",
                            "distance": 150,
                            "maneuver": {"type": "new name", "modifier": "straight"},
                        },
                        {"name": "Monas", "distance": 0, "maneuver": {"type": "arrive"}},
                    ]
                }
            ],
        }
    ],
}


def test_parse_osrm_route():
    route = parse_osrm_route(OSRM_SAMPLE, "Monas")
    assert route.distance_m == 1234.5
    assert [s.maneuver for s in route.steps] == ["depart", "turn", "roundabout", "new name", "arrive"]
    assert route.steps[1].modifier == "left"
    assert route.steps[2].exit == 2


@pytest.mark.parametrize("data", [{"code": "NoRoute"}, {"code": "Ok", "routes": []}])
def test_parse_osrm_no_route(data):
    with pytest.raises(NavigationError) as err:
        parse_osrm_route(data, "x")
    assert err.value.kind == "no_route"


def test_describe_steps_indonesian():
    tr = Translator("id")
    steps = parse_osrm_route(OSRM_SAMPLE, "Monas").steps
    texts = [describe_step(s, tr) for s in steps]
    assert texts[0] == "Mulai berjalan ke Jalan Kebon Sirih, lalu jalan sekitar 120 meter."
    assert texts[1] == "Belok kiri ke Jalan Medan Merdeka Selatan, lalu jalan sekitar 640 meter."
    assert texts[2] == "Masuk bundaran, ambil jalan keluar ke-2, lalu jalan sekitar 300 meter."
    assert texts[3] == "Jalan lurus ke Jalan Thamrin, lalu jalan sekitar 150 meter."
    assert texts[4] == "Kamu tiba di tujuan, Monas."


def test_describe_steps_english():
    tr = Translator("en")
    step = RouteStep("turn", "slight right", "Main Street", 1500)
    assert describe_step(step, tr) == "Bear slightly right onto Main Street, then walk about 1.5 kilometers."


def test_every_osrm_modifier_has_a_message():
    tr = Translator("id")
    for modifier in [
        "uturn",
        "sharp right",
        "right",
        "slight right",
        "straight",
        "slight left",
        "left",
        "sharp left",
    ]:
        text = describe_step(RouteStep("turn", modifier, "", 10), tr)
        assert not text.startswith("modifier_")


def test_session_navigation():
    session = NavigationSession(parse_osrm_route(OSRM_SAMPLE, "Monas"))
    assert session.current.maneuver == "depart"
    visited = [session.current.maneuver]
    while (step := session.advance()) is not None:
        visited.append(step.maneuver)
    assert visited[-1] == "arrive"
    assert session.finished
    assert session.advance() is None


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


HERE = Location(-6.18, 106.82, "Jakarta", 5000, "ip")


def test_geocode_and_route_happy_path():
    session = FakeSession(
        [FakeResponse([{"lat": "-6.1754", "lon": "106.8272", "name": "Monas"}]), FakeResponse(OSRM_SAMPLE)]
    )
    nav = Navigator(NavigationSettings(http_timeout_s=3), session=session)
    place = nav.geocode("monas", near=HERE)
    assert place == Place("Monas", -6.1754, 106.8272)
    route = nav.route(HERE, place)
    assert route.destination == "Monas"
    assert nav.walking_minutes(route) == 17
    geo_url, geo_params, timeout = session.calls[0]
    assert geo_params["bounded"] == 0 and "viewbox" in geo_params
    assert timeout == 3
    assert session.calls[1][0].startswith("https://router.project-osrm.org/route/v1/foot/106.82,-6.18;")
    assert "aiforus" in session.headers["User-Agent"]


def test_geocode_not_found():
    nav = Navigator(NavigationSettings(), session=FakeSession([FakeResponse([])]))
    with pytest.raises(NavigationError) as err:
        nav.geocode("tempat antah berantah")
    assert err.value.kind == "not_found"


@pytest.mark.parametrize("failure", [requests.ConnectionError("offline"), FakeResponse({}, 503)])
def test_network_errors_are_mapped(failure):
    nav = Navigator(NavigationSettings(), session=FakeSession([failure]))
    with pytest.raises(NavigationError) as err:
        nav.geocode("monas")
    assert err.value.kind == "network"
