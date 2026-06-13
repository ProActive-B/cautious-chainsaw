"""Gather location attributes for a clicked point.

Produces the LocationAttributes that the rules engine and risk scoring consume:
airspace class, nearest airport, population/building/RF bands, and boolean zone
flags (e.g. critical_infrastructure_zone) that trigger location-predicated rules.
"""

from __future__ import annotations

from ..models import LocationAttributes, NearbyAircraft
from .seed import haversine_nm, load_seed


def _band_from_density(density: float | None) -> str | None:
    if density is None:
        return None
    if density >= 1000:
        return "high"
    if density >= 300:
        return "medium"
    return "low"


def gather(lat: float, lon: float, aircraft: list[NearbyAircraft] | None = None) -> LocationAttributes:
    seed = load_seed()
    notes: list[str] = [
        "Attributes derived from SAMPLE pilot staging data; not authoritative."
    ]

    # --- Airspace + nearest airport ---
    airspace_class: str | None = None
    uasfm_ceiling: int | None = None
    nearest_airport: str | None = None
    nearest_dist: float | None = None

    for ap in seed.get("airports", []):
        d = haversine_nm(lat, lon, ap["lat"], ap["lon"])
        if nearest_dist is None or d < nearest_dist:
            nearest_dist = d
            nearest_airport = f"{ap['name']} ({ap['ident']})"
        if d <= ap["radius_nm"]:
            # Innermost controlled airspace wins (smaller radius = closer-in).
            if airspace_class is None or ap["radius_nm"] < _radius_of(seed, airspace_class):
                airspace_class = ap["airspace_class"]
                uasfm_ceiling = ap.get("uasfm_ceiling_ft")
    if airspace_class is None:
        airspace_class = "G/E"  # uncontrolled / general

    # --- Population / building / RF bands ---
    density: float | None = None
    place_label = "Texas (sample area)"
    for area in seed.get("population_areas", []):
        if haversine_nm(lat, lon, area["lat"], area["lon"]) <= area["radius_nm"]:
            # Densest containing area wins.
            if density is None or area["density_per_km2"] > density:
                density = area["density_per_km2"]
                place_label = area["label"]
    pop_band = _band_from_density(density)
    rf_congestion = "high" if (pop_band == "high" or (nearest_dist or 99) < 5) else pop_band

    # --- Zone flags ---
    flags: dict[str, bool] = {}
    for zone in seed.get("zones", []):
        if haversine_nm(lat, lon, zone["lat"], zone["lon"]) <= zone["radius_nm"]:
            flags[zone["flag"]] = True
            place_label = zone["label"]
            notes.append(f"Inside zone: {zone['label']}")

    return LocationAttributes(
        lat=lat,
        lon=lon,
        place_label=place_label,
        airspace_class=airspace_class,
        uasfm_ceiling_ft=uasfm_ceiling,
        nearest_airport=nearest_airport,
        nearest_airport_distance_nm=round(nearest_dist, 1) if nearest_dist is not None else None,
        population_density_per_km2=density,
        building_density=pop_band,
        rf_congestion=rf_congestion,
        location_flags=flags,
        nearby_aircraft=aircraft or [],
        notes=notes,
    )


def _radius_of(seed: dict, airspace_class: str) -> float:
    for ap in seed.get("airports", []):
        if ap["airspace_class"] == airspace_class:
            return ap["radius_nm"]
    return 9999.0
