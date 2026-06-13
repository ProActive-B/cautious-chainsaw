"""Gather location attributes for a clicked point.

Produces the LocationAttributes that the rules engine and risk scoring consume.
Airspace comes from live FAA data when staged (backend/data/faa/), falling back
to the sample seed circles otherwise. Population, buildings, and bespoke zones
(critical-infrastructure, stadium, etc.) still come from the seed pending real
data. Live aircraft and TFRs are passed in by the API layer (kept out of here so
this stays pure and unit-testable without network).
"""

from __future__ import annotations

from shapely.geometry import Point, shape

from ..feeds import faa
from ..models import LocationAttributes, NearbyAircraft
from .seed import haversine_nm, load_seed

AIRCRAFT_RADIUS_NM = 10.0


def _band_from_density(density: float | None) -> str | None:
    if density is None:
        return None
    if density >= 1000:
        return "high"
    if density >= 300:
        return "medium"
    return "low"


def gather(
    lat: float,
    lon: float,
    aircraft: list[dict] | None = None,
    tfr_result: dict | None = None,
    population: dict | None = None,
    buildings: dict | None = None,
) -> LocationAttributes:
    seed = load_seed()
    notes: list[str] = []
    flags: dict[str, bool] = {}

    airspace_class, uasfm_ceiling, nearest_airport, nearest_dist = _airspace(lat, lon, seed, flags, notes)

    # --- Population density: live US Census ACS if provided, else sample seed ---
    place_label = "Texas (sample area)"
    if population:
        density = population.get("density_per_km2")
        notes.append(f"Population from US Census ACS ({population.get('tract')}).")
    else:
        density = None
        for area in seed.get("population_areas", []):
            if haversine_nm(lat, lon, area["lat"], area["lon"]) <= area["radius_nm"]:
                if density is None or area["density_per_km2"] > density:
                    density = area["density_per_km2"]
                    place_label = area["label"]
        notes.append("Population is SAMPLE data (Census feed unavailable).")
    pop_band = _band_from_density(density)

    # --- Building density: live OpenStreetMap if provided, else mirror population ---
    if buildings:
        building_band = buildings.get("band")
        building_count = buildings.get("count")
        notes.append(f"Buildings from OpenStreetMap ({building_count} within {buildings.get('radius_m')} m).")
    else:
        building_band = pop_band
        building_count = None

    near_airport = (nearest_dist or 99) < 5
    rf_congestion = "high" if (pop_band == "high" or building_band == "high" or near_airport) else (pop_band or building_band)

    # --- Bespoke zones (critical infrastructure, stadium, ...) from seed ---
    for zone in seed.get("zones", []):
        if haversine_nm(lat, lon, zone["lat"], zone["lon"]) <= zone["radius_nm"]:
            flags[zone["flag"]] = True
            place_label = zone["label"]
            notes.append(f"Inside zone: {zone['label']}")

    # --- Live aircraft + TFRs (provided by API) ---
    nearby = _nearby_aircraft(lat, lon, aircraft or [])
    active_tfr, tfr_names = _tfrs(lat, lon, tfr_result, notes)

    return LocationAttributes(
        lat=lat,
        lon=lon,
        place_label=place_label,
        airspace_class=airspace_class,
        uasfm_ceiling_ft=uasfm_ceiling,
        nearest_airport=nearest_airport,
        nearest_airport_distance_nm=round(nearest_dist, 1) if nearest_dist is not None else None,
        population_density_per_km2=density,
        building_density=building_band,
        building_count=building_count,
        rf_congestion=rf_congestion,
        location_flags=flags,
        active_tfr=active_tfr,
        active_tfr_names=tfr_names,
        nearby_aircraft=nearby,
        notes=notes,
    )


def _airspace(lat, lon, seed, flags, notes):
    """Return (airspace_class, uasfm_ceiling_ft, nearest_airport, nearest_dist_nm)."""
    if faa.has_data():
        inside = faa.airspace_at(lat, lon)
        if inside:
            notes.append(f"Inside Class {inside['class']} airspace ({inside['name']}).")
            airspace_class, nearest_airport, nearest_dist = inside["class"], inside["name"], 0.0
        else:
            airspace_class = "E/G"
            nc = faa.nearest_controlled(lat, lon)
            nearest_airport, nearest_dist = (nc[0], nc[1]) if nc else (None, None)
        for s in faa.sua_at(lat, lon):
            flags["special_use_airspace"] = True
            notes.append(f"Special-use airspace: {s['name']} ({s['type']})")
        notes.append("Airspace from live FAA data; population/zones are sample data.")
        return airspace_class, None, nearest_airport, nearest_dist

    # Fallback: sample seed circles.
    notes.append("Attributes derived from SAMPLE pilot staging data; not authoritative.")
    airspace_class, uasfm_ceiling, nearest_airport, nearest_dist = None, None, None, None
    for ap in seed.get("airports", []):
        d = haversine_nm(lat, lon, ap["lat"], ap["lon"])
        if nearest_dist is None or d < nearest_dist:
            nearest_dist = d
            nearest_airport = f"{ap['name']} ({ap['ident']})"
        if d <= ap["radius_nm"] and (airspace_class is None or ap["radius_nm"] < _radius_of(seed, airspace_class)):
            airspace_class = ap["airspace_class"]
            uasfm_ceiling = ap.get("uasfm_ceiling_ft")
    if airspace_class is None:
        airspace_class = "G/E"
    return airspace_class, uasfm_ceiling, nearest_airport, nearest_dist


def _nearby_aircraft(lat: float, lon: float, aircraft: list[dict]) -> list[NearbyAircraft]:
    out: list[NearbyAircraft] = []
    for ac in aircraft:
        if ac.get("on_ground") or ac.get("lat") is None or ac.get("lon") is None:
            continue
        d = haversine_nm(lat, lon, ac["lat"], ac["lon"])
        if d > AIRCRAFT_RADIUS_NM:
            continue
        try:
            out.append(
                NearbyAircraft(
                    icao24=ac.get("icao24"),
                    callsign=ac.get("callsign"),
                    distance_nm=round(d, 1),
                    altitude_ft_agl=ac.get("alt_ft"),
                )
            )
        except Exception:  # noqa: BLE001 — one malformed feed entry must not 500 an assessment
            continue
    out.sort(key=lambda a: a.distance_nm)
    return out[:12]


def _tfrs(lat, lon, tfr_result, notes) -> tuple[bool, list[str]]:
    if not tfr_result:
        return False, []
    if tfr_result.get("note"):
        notes.append(tfr_result["note"])
    active, names = False, []
    pt = Point(lon, lat)
    for t in tfr_result.get("tfrs", []):
        geom = t.get("geometry")
        if geom is None or shape(geom).contains(pt):
            active = True
            names.append(t["name"])
    return active, names


def _radius_of(seed: dict, airspace_class: str) -> float:
    for ap in seed.get("airports", []):
        if ap["airspace_class"] == airspace_class:
            return ap["radius_nm"]
    return 9999.0
