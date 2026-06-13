"""Build GeoJSON FeatureCollections for the map.

Airspace + special-use airspace come from the staged live FAA data when present
(annotated for styling/popups); zones, population, and the pilot site come from
the seed. Falls back to seed airspace circles when FAA data isn't staged.
"""

from __future__ import annotations

import functools
import json

from ..config import settings
from ..feeds import faa
from .seed import geodesic_circle, load_seed


def _circle_feature(lat: float, lon: float, radius_nm: float, props: dict) -> dict:
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "Polygon", "coordinates": [geodesic_circle(lat, lon, radius_nm)]},
    }


def _point_feature(lat: float, lon: float, props: dict) -> dict:
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


@functools.lru_cache(maxsize=2)
def _faa_fc(filename: str, kind: str) -> dict:
    """Load a staged FAA GeoJSON file and annotate features for the map."""
    data = json.loads((settings.data_dir / "faa" / filename).read_text(encoding="utf-8"))
    for feat in data.get("features", []):
        p = feat.setdefault("properties", {})
        name = (p.get("NAME") or "").title()
        if kind == "airspace":
            p["kind"] = "airspace"
            p["airspace_class"] = p.get("CLASS")
            p["label"] = f"Class {p.get('CLASS')} — {name}"
        else:
            p["kind"] = "sua"
            p["label"] = f"{p.get('TYPE_CODE') or 'SUA'}: {name}"
    return data


def build_layers() -> dict[str, dict]:
    seed = load_seed()

    population = [
        _circle_feature(a["lat"], a["lon"], a["radius_nm"],
                        {"kind": "population", "label": a["label"], "density_per_km2": a["density_per_km2"]})
        for a in seed.get("population_areas", [])
    ]
    zones = [
        _circle_feature(z["lat"], z["lon"], z["radius_nm"],
                        {"kind": "zone", "flag": z["flag"], "label": z["label"]})
        for z in seed.get("zones", [])
    ]
    site = seed["pilot_site"]
    sites = [_point_feature(site["lat"], site["lon"], {"kind": "site", "label": site["label"]})]

    if faa.has_data():
        airspace = _faa_fc("class_airspace_tx.geojson", "airspace")
        sua = _faa_fc("sua_tx.geojson", "sua")
    else:
        airspace = {
            "type": "FeatureCollection",
            "features": [
                _circle_feature(ap["lat"], ap["lon"], ap["radius_nm"],
                                {"kind": "airspace", "airspace_class": ap["airspace_class"],
                                 "label": f"Class {ap['airspace_class']} — {ap['name']}"})
                for ap in seed.get("airports", [])
            ],
        }
        sua = {"type": "FeatureCollection", "features": []}

    return {
        "airspace": airspace,
        "sua": sua,
        "population": {"type": "FeatureCollection", "features": population},
        "zones": {"type": "FeatureCollection", "features": zones},
        "sites": {"type": "FeatureCollection", "features": sites},
    }
