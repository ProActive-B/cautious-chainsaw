"""Tests for live-feed wiring and real FAA airspace lookups.

These avoid the network: FAA lookups read the staged GeoJSON on disk, and
aircraft/TFR handling is exercised by injecting data into gather() the same way
the API layer does after fetching.
"""

from __future__ import annotations

import pytest

from app.feeds import faa
from app.spatial.attributes import gather

# DFW airport sits inside Dallas Class B (surface).
DFW_LAT, DFW_LON = 32.8998, -97.0403

faa_staged = pytest.mark.skipif(not faa.has_data(), reason="FAA data not staged")


@faa_staged
def test_airspace_at_dfw_is_class_b():
    a = faa.airspace_at(DFW_LAT, DFW_LON)
    assert a is not None
    assert a["class"] == "B"
    assert "DALLAS" in (a["name"] or "").upper()


@faa_staged
def test_uncontrolled_point_reports_nearest():
    # Far west Texas desert — outside Class B/C/D.
    a = faa.airspace_at(31.0, -104.5)
    assert a is None
    nc = faa.nearest_controlled(31.0, -104.5)
    assert nc is not None and nc[1] > 0


@faa_staged
def test_gather_uses_real_airspace_at_dfw():
    loc = gather(DFW_LAT, DFW_LON)
    assert loc.airspace_class == "B"


def test_nearby_aircraft_filtering():
    aircraft = [
        {"icao24": "near1", "callsign": "AAL1", "lat": 32.95, "lon": -96.66, "alt_ft": 800, "on_ground": False},
        {"icao24": "far1", "callsign": "FAR", "lat": 30.0, "lon": -98.0, "alt_ft": 5000, "on_ground": False},
        {"icao24": "grnd1", "callsign": "TAXI", "lat": 32.95, "lon": -96.65, "alt_ft": 0, "on_ground": True},
    ]
    loc = gather(32.95, -96.65, aircraft=aircraft)
    ids = [a.icao24 for a in loc.nearby_aircraft]
    assert "near1" in ids          # within 10 nm, airborne
    assert "far1" not in ids       # too far
    assert "grnd1" not in ids      # on ground


def test_nearby_aircraft_tolerates_null_icao24_and_alt():
    # Community feeds (TIS-B/MLAT) can omit hex/altitude — must not 500 an assess.
    aircraft = [
        {"icao24": None, "callsign": "TISB", "lat": 32.95, "lon": -96.66, "alt_ft": 800, "on_ground": False},
        {"icao24": "abc123", "callsign": None, "lat": 32.95, "lon": -96.66, "alt_ft": None, "on_ground": False},
    ]
    loc = gather(32.95, -96.65, aircraft=aircraft)
    assert len(loc.nearby_aircraft) == 2


def test_gather_uses_injected_population_and_buildings():
    loc = gather(
        32.95, -96.65,
        population={"density_per_km2": 1800, "tract": "Census Tract 1"},
        buildings={"count": 140, "band": "high", "radius_m": 500},
    )
    assert loc.population_density_per_km2 == 1800
    assert loc.building_density == "high"
    assert loc.building_count == 140
    assert loc.rf_congestion == "high"


def test_gather_uses_injected_terrain():
    loc = gather(
        32.95, -96.65,
        terrain={"elevation_m": 1850.0, "relief_m": 120.0, "terrain": "rugged", "high_ground": True},
    )
    assert loc.elevation_m == 1850.0
    assert loc.terrain == "rugged"
    assert loc.high_ground is True


def test_tfr_note_surfaced_when_unconfigured():
    tfr = {"configured": False, "tfrs": [], "note": "TFR feed not configured."}
    loc = gather(32.95, -96.65, tfr_result=tfr)
    assert loc.active_tfr is False
    assert any("not configured" in n for n in loc.notes)


def test_tfr_polygon_containment():
    tfr = {
        "configured": True,
        "tfrs": [{
            "name": "TEST TFR",
            "geometry": {"type": "Polygon", "coordinates": [[
                [-96.7, 32.9], [-96.6, 32.9], [-96.6, 33.0], [-96.7, 33.0], [-96.7, 32.9]]]},
        }],
    }
    loc = gather(32.95, -96.65, tfr_result=tfr)
    assert loc.active_tfr is True
    assert "TEST TFR" in loc.active_tfr_names
