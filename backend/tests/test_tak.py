"""TAK export tests: CoT XML validity, data-package structure, endpoints."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

from fastapi.testclient import TestClient

from app.feeds import adsb, buildings, census, notam, terrain as terrain_feed
from app.main import app
from app.models import AssessRequest
from app.report import build_report
from app.spatial.attributes import gather
from app.tak import cot, datapackage

client = TestClient(app)


def _report():
    loc = gather(32.95, -96.65)  # seed fallback, no network
    return build_report(AssessRequest(profile="ci_owner", lat=32.95, lon=-96.65), loc)


# --- pure CoT / data-package ---
def test_assessment_cot_is_valid_cot():
    xml = cot.assessment_cot(_report())
    root = ET.fromstring(xml.encode("utf-8"))
    assert root.tag == "event"
    assert root.attrib["type"] == "b-m-p-s-m"
    assert root.find("point") is not None
    remarks = root.find("detail/remarks").text
    assert "CUAS Decision Map" in remarks
    assert "DECISION SUPPORT ONLY" in remarks


def test_aircraft_cot_is_air_track():
    xml = cot.aircraft_cot(
        {"icao24": "abc123", "callsign": "AAL1", "lat": 32.9, "lon": -97.0, "alt_ft": 3000, "track": 90}
    )
    root = ET.fromstring(xml.encode("utf-8"))
    assert root.attrib["type"] == "a-n-A-C-F"
    assert root.find("detail/contact").attrib["callsign"] == "AAL1"


def test_datapackage_zip_structure():
    pkg = datapackage.build_package(cot.assessment_cot(_report()), uid="CUAS.TEST")
    z = zipfile.ZipFile(io.BytesIO(pkg))
    names = z.namelist()
    assert "MANIFEST/manifest.xml" in names
    assert "assessment.cot" in names
    assert "MissionPackageManifest" in z.read("MANIFEST/manifest.xml").decode()


# --- endpoints (feeds stubbed, no network) ---
async def _no_air(*_a, **_k):
    return [{"icao24": "a1", "callsign": "AAL1", "lat": 32.95, "lon": -96.66, "alt_ft": 900, "on_ground": False, "track": 45}]


async def _no_tfr(*_a, **_k):
    return {"configured": False, "tfrs": [], "note": ""}


async def _none(*_a, **_k):
    return None


def _stub(monkeypatch):
    monkeypatch.setattr(adsb, "fetch_aircraft", _no_air)
    monkeypatch.setattr(notam, "fetch_tfrs", _no_tfr)
    monkeypatch.setattr(census, "population_density", _none)
    monkeypatch.setattr(buildings, "building_density", _none)
    monkeypatch.setattr(terrain_feed, "terrain", _none)


def test_cot_assessment_endpoint(monkeypatch):
    _stub(monkeypatch)
    r = client.post("/api/cot/assessment", json={"profile": "ci_owner", "lat": 32.95, "lon": -96.65})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    assert "<event" in r.text


def test_datapackage_endpoint(monkeypatch):
    _stub(monkeypatch)
    r = client.post("/api/tak/datapackage", json={"profile": "ci_owner", "lat": 32.95, "lon": -96.65})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert "MANIFEST/manifest.xml" in z.namelist()


def test_cot_aircraft_endpoint(monkeypatch):
    _stub(monkeypatch)
    r = client.get("/api/cot/aircraft?lamin=32&lomin=-98&lamax=33&lomax=-96")
    assert r.status_code == 200
    assert "a-n-A-C-F" in r.text
