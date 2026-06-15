"""Endpoint-level tests via TestClient (network stubbed).

These exercise the full request/response cycle — including response_model
validation and feed wiring — which unit tests on gather()/build_report() miss.
Regression guard for the assess NameError (opensky vs adsb) bug.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.feeds import adsb, buildings, census, notam, terrain as terrain_feed
from app.main import app

client = TestClient(app)


async def _fake_aircraft(*_a, **_k):
    return [
        {"icao24": "abc123", "callsign": "AAL1", "lat": 32.95, "lon": -96.66,
         "alt_ft": 800, "on_ground": False},
        {"icao24": None, "callsign": "TISB", "lat": 32.94, "lon": -96.65,
         "alt_ft": None, "on_ground": False},  # malformed entry must not 500
    ]


async def _fake_tfr(*_a, **_k):
    return {"configured": False, "tfrs": [], "note": "TFR feed not configured."}


async def _fake_pop(*_a, **_k):
    return {"density_per_km2": 1800.0, "tract": "Census Tract 1", "source": "ACS"}


async def _fake_buildings(*_a, **_k):
    return {"count": 140, "band": "high", "radius_m": 500, "source": "OSM"}


async def _fake_terrain(*_a, **_k):
    return {"elevation_m": 131.0, "relief_m": 25.0, "terrain": "rolling",
            "high_ground": False, "source": "USGS 3DEP"}


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_aircraft_endpoint_ok(monkeypatch):
    monkeypatch.setattr(adsb, "fetch_aircraft", _fake_aircraft)
    r = client.get("/api/aircraft?lamin=32&lomin=-98&lamax=33&lomax=-96")
    assert r.status_code == 200
    assert r.json()["count"] == 2


def test_assess_endpoint_ok(monkeypatch):
    monkeypatch.setattr(adsb, "fetch_aircraft", _fake_aircraft)
    monkeypatch.setattr(notam, "fetch_tfrs", _fake_tfr)
    monkeypatch.setattr(census, "population_density", _fake_pop)
    monkeypatch.setattr(buildings, "building_density", _fake_buildings)
    monkeypatch.setattr(terrain_feed, "terrain", _fake_terrain)
    r = client.post(
        "/api/assess",
        json={"profile": "federal_124n", "lat": 32.8998, "lon": -97.0403, "credible_threat": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert {"permitted", "conditional", "prohibited", "documentation"} <= body.keys()
    # Real population + buildings flow into the location.
    assert body["location"]["population_density_per_km2"] == 1800.0
    assert body["location"]["building_count"] == 140
    assert body["location"]["terrain"] == "rolling"
    assert body["location"]["elevation_m"] == 131.0
    # The malformed (null-icao24) aircraft must not break the response.
    assert isinstance(body["location"]["nearby_aircraft"], list)
