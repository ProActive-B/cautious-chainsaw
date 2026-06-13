"""Live ADS-B aircraft via keyless community APIs (adsb.lol / airplanes.live).

OpenSky blocks datacenter IPs at the network level (ConnectTimeout from cloud
hosts like Render), so these community feeds — which use the readsb "re-api"
JSON format and are cloud-friendly — are the default. Point+radius based, so we
convert the requested bbox to a center+radius. Cached ~10 s and fail-safe to an
empty list so an assessment never breaks on a feed outage.

re-api altitudes (alt_baro) are already in FEET; "ground" denotes on-ground.
"""

from __future__ import annotations

import math

import httpx

from .cache import TTLCache

# Provider URL templates: {lat},{lon} center and {dist} radius in nm.
_PROVIDERS = [
    ("adsb.lol", "https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{dist}"),
    ("airplanes.live", "https://api.airplanes.live/v2/point/{lat}/{lon}/{dist}"),
]
_HEADERS = {"User-Agent": "cuas-decision-map/1.0 (+https://github.com/ProActive-B/cautious-chainsaw)"}
_MAX_RADIUS_NM = 250

_cache = TTLCache(ttl_seconds=10)
last_status: dict = {"provider": None, "http_status": None, "count": None, "error": None}


def _bbox_to_center_radius(lamin, lomin, lamax, lomax) -> tuple[float, float, int]:
    clat, clon = (lamin + lamax) / 2, (lomin + lomax) / 2
    dlat_nm = abs(lamax - lamin) / 2 * 60
    dlon_nm = abs(lomax - lomin) / 2 * 60 * math.cos(math.radians(clat))
    radius = math.ceil(math.hypot(dlat_nm, dlon_nm))
    return clat, clon, max(1, min(radius, _MAX_RADIUS_NM))


def _parse(data: dict) -> list[dict]:
    out: list[dict] = []
    for ac in data.get("ac") or []:
        lat, lon = ac.get("lat"), ac.get("lon")
        if lat is None or lon is None:
            continue
        alt = ac.get("alt_baro")
        out.append(
            {
                "icao24": ac.get("hex"),
                "callsign": (ac.get("flight") or "").strip() or None,
                "lat": lat,
                "lon": lon,
                "alt_ft": alt if isinstance(alt, (int, float)) else None,
                "on_ground": alt == "ground",
                "track": ac.get("track"),
            }
        )
    return out


async def fetch_aircraft(
    lamin: float, lomin: float, lamax: float, lomax: float, use_cache: bool = True
) -> list[dict]:
    key = f"{lamin:.2f},{lomin:.2f},{lamax:.2f},{lomax:.2f}"
    if use_cache:
        cached = _cache.get(key)
        if cached is not None:
            return cached

    clat, clon, dist = _bbox_to_center_radius(lamin, lomin, lamax, lomax)
    aircraft: list[dict] = []
    last_status["provider"] = None
    last_status["error"] = None

    async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
        for name, tmpl in _PROVIDERS:
            url = tmpl.format(lat=f"{clat:.4f}", lon=f"{clon:.4f}", dist=dist)
            try:
                resp = await client.get(url)
                last_status["provider"] = name
                last_status["http_status"] = resp.status_code
                resp.raise_for_status()
                aircraft = _parse(resp.json())
                last_status["count"] = len(aircraft)
                last_status["error"] = None
                break  # provider succeeded
            except Exception as exc:  # noqa: BLE001 — try next provider, then fail safe
                last_status["error"] = f"{name}: {type(exc).__name__}: {str(exc)[:120]}"
                continue

    _cache.set(key, aircraft)
    return aircraft
