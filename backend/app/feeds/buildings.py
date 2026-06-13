"""Real building density from OpenStreetMap via the Overpass API.

Counts building footprints within a radius of the point (keyless, cloud-friendly,
uses ``out count;`` so no geometry is transferred). Maps the count to a band that
feeds the RF/urban context and the report. Cached and fail-safe to None.
"""

from __future__ import annotations

import httpx

from .cache import TTLCache

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_HEADERS = {"User-Agent": "cuas-decision-map/1.0"}
_cache = TTLCache(ttl_seconds=21600)  # 6 h; building footprints change slowly
last_status: dict = {"http_status": None, "error": None, "count": None}

DEFAULT_RADIUS_M = 500


def _band(count: int) -> str:
    # Within a 500 m radius (~0.79 km²): tuned for low/medium/high built-up areas.
    if count >= 100:
        return "high"
    if count >= 20:
        return "medium"
    return "low"


async def building_density(lat: float, lon: float, radius_m: int = DEFAULT_RADIUS_M) -> dict | None:
    key = f"{lat:.3f},{lon:.3f}:{radius_m}"
    cached = _cache.get(key)
    if cached is not None:
        return cached

    q = (
        f"[out:json][timeout:25];"
        f'(way["building"](around:{radius_m},{lat},{lon});'
        f'relation["building"](around:{radius_m},{lat},{lon}););'
        f"out count;"
    )
    try:
        async with httpx.AsyncClient(timeout=30, headers=_HEADERS) as client:
            resp = await client.get(OVERPASS_URL, params={"data": q})
            last_status["http_status"] = resp.status_code
            resp.raise_for_status()
            els = resp.json().get("elements") or []
            count = int(els[0]["tags"]["total"]) if els else 0
            result = {
                "count": count,
                "band": _band(count),
                "radius_m": radius_m,
                "source": "OpenStreetMap buildings (Overpass)",
            }
            last_status.update({"error": None, "count": count})
            _cache.set(key, result)
            return result
    except Exception as exc:  # noqa: BLE001 — fall back to sample data on outage
        last_status["error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        return None
