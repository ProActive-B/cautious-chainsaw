"""Endpoint-level tests via TestClient (network stubbed).

These exercise the full request/response cycle — including response_model
validation and feed wiring — which unit tests on gather()/build_report() miss.
Regression guard for the assess NameError (opensky vs adsb) bug.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.feeds import adsb, notam
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
    r = client.post(
        "/api/assess",
        json={"profile": "federal_124n", "lat": 32.8998, "lon": -97.0403, "credible_threat": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert {"permitted", "conditional", "prohibited", "documentation"} <= body.keys()
    # The malformed (null-icao24) aircraft must not break the response.
    assert isinstance(body["location"]["nearby_aircraft"], list)
