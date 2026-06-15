"""Terrain context from USGS 3DEP elevation (keyless).

One ``getSamples`` call to the 3DEP ImageServer returns elevation for the point
plus a ring of samples, which we reduce to: elevation, local relief (max-min),
a terrain band, and whether the point sits on local high ground. These drive
line-of-sight-dependent considerations (HEL beam path, RF/EO-IR masking).
Cached (terrain is static) and fail-safe to None.
"""

from __future__ import annotations

import math

import httpx

from .cache import TTLCache

GETSAMPLES_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/getSamples"
)
_HEADERS = {"User-Agent": "cuas-decision-map/1.0"}
_cache = TTLCache(ttl_seconds=86400)  # 24 h; terrain is static
last_status: dict = {"http_status": None, "error": None, "elevation_m": None}

RING_RADIUS_KM = 1.5
RING_POINTS = 8


def _ring(lat: float, lon: float) -> list[list[float]]:
    """Center point first, then a ring of points ~RING_RADIUS_KM around it."""
    pts = [[lon, lat]]
    dlat = RING_RADIUS_KM / 111.32
    dlon = RING_RADIUS_KM / (111.32 * max(0.1, math.cos(math.radians(lat))))
    for i in range(RING_POINTS):
        ang = 2 * math.pi * i / RING_POINTS
        pts.append([lon + dlon * math.cos(ang), lat + dlat * math.sin(ang)])
    return pts


def _band(relief_m: float) -> str:
    if relief_m >= 75:
        return "rugged"
    if relief_m >= 15:
        return "rolling"
    return "flat"


async def terrain(lat: float, lon: float) -> dict | None:
    key = f"{lat:.3f},{lon:.3f}"
    cached = _cache.get(key)
    if cached is not None:
        return cached

    import json

    geometry = json.dumps({"points": _ring(lat, lon), "spatialReference": {"wkid": 4326}})
    body = {
        "geometry": geometry,
        "geometryType": "esriGeometryMultipoint",
        "returnFirstValueOnly": "true",
        "f": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=25, headers=_HEADERS) as client:
            resp = await client.post(GETSAMPLES_URL, data=body)
            last_status["http_status"] = resp.status_code
            resp.raise_for_status()
            samples = resp.json().get("samples") or []
            vals: list[float] = []
            for s in samples:
                try:
                    vals.append(float(s["value"]))
                except (KeyError, TypeError, ValueError):
                    continue
            if not vals:
                last_status["error"] = "no elevation samples"
                return None
            center = vals[0]
            ring = vals[1:] or vals
            relief = max(vals) - min(vals)
            result = {
                "elevation_m": round(center, 1),
                "relief_m": round(relief, 1),
                "terrain": _band(relief),
                "high_ground": center > (sum(ring) / len(ring)) + 5,
                "source": "USGS 3DEP",
            }
            last_status.update({"error": None, "elevation_m": result["elevation_m"]})
            _cache.set(key, result)
            return result
    except Exception as exc:  # noqa: BLE001 — fall back gracefully on outage
        last_status["error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        return None
