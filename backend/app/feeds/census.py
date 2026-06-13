"""Real population density from the US Census ACS (via Esri Living Atlas).

Queries the public ACS Total Population tract layer by point — keyless and
cloud-friendly — and returns people/km² for the containing tract (total
population B01001_001E ÷ land area ALAND). Cached (tracts are static) and
fail-safe to None so an assessment falls back to sample data on any outage.
"""

from __future__ import annotations

import httpx

from .cache import TTLCache

ACS_URL = (
    "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/"
    "ACS_Total_Population_Boundaries/FeatureServer/2/query"
)
_HEADERS = {"User-Agent": "cuas-decision-map/1.0"}
_cache = TTLCache(ttl_seconds=21600)  # 6 h; tract density doesn't change
last_status: dict = {"http_status": None, "error": None, "density": None}


async def population_density(lat: float, lon: float) -> dict | None:
    key = f"{lat:.3f},{lon:.3f}"
    cached = _cache.get(key)
    if cached is not None:
        return cached

    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "NAME,B01001_001E,ALAND",
        "returnGeometry": "false",
        "f": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
            resp = await client.get(ACS_URL, params=params)
            last_status["http_status"] = resp.status_code
            resp.raise_for_status()
            feats = resp.json().get("features") or []
            if not feats:
                last_status["error"] = "no tract at point"
                return None
            a = feats[0]["attributes"]
            pop, aland = a.get("B01001_001E"), a.get("ALAND")
            if pop is None or not aland or aland <= 0:
                return None
            density = round(pop / (aland / 1e6), 1)
            result = {
                "density_per_km2": density,
                "tract": a.get("NAME"),
                "source": "US Census ACS (B01001_001E)",
            }
            last_status.update({"error": None, "density": density})
            _cache.set(key, result)
            return result
    except Exception as exc:  # noqa: BLE001 — fall back to sample data on outage
        last_status["error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        return None
