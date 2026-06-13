"""Build GeoJSON FeatureCollections for the map from the same seed definitions.

One source of truth (data/seed/tx_pilot.json) drives both the attribute logic
and what the user sees, so the map never disagrees with the assessment.
"""

from __future__ import annotations

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


def build_layers() -> dict[str, dict]:
    seed = load_seed()
    layers: dict[str, list[dict]] = {
        "airspace": [],
        "zones": [],
        "population": [],
        "sites": [],
    }

    for ap in seed.get("airports", []):
        layers["airspace"].append(
            _circle_feature(
                ap["lat"], ap["lon"], ap["radius_nm"],
                {"kind": "airspace", "airspace_class": ap["airspace_class"],
                 "label": f"Class {ap['airspace_class']} — {ap['name']}",
                 "ident": ap["ident"], "uasfm_ceiling_ft": ap.get("uasfm_ceiling_ft")},
            )
        )

    for area in seed.get("population_areas", []):
        layers["population"].append(
            _circle_feature(
                area["lat"], area["lon"], area["radius_nm"],
                {"kind": "population", "label": area["label"],
                 "density_per_km2": area["density_per_km2"]},
            )
        )

    for zone in seed.get("zones", []):
        layers["zones"].append(
            _circle_feature(
                zone["lat"], zone["lon"], zone["radius_nm"],
                {"kind": "zone", "flag": zone["flag"], "label": zone["label"]},
            )
        )

    site = seed["pilot_site"]
    layers["sites"].append(
        _point_feature(site["lat"], site["lon"], {"kind": "site", "label": site["label"]})
    )

    return {
        name: {"type": "FeatureCollection", "features": feats}
        for name, feats in layers.items()
    }
