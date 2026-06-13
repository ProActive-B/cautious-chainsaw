"""Live ADS-B aircraft via the OpenSky Network REST API.

Returns aircraft state vectors within a bounding box. Uses OAuth2 client
credentials when configured (higher limits); otherwise falls back to anonymous
access. Cached ~10 s to respect rate limits. Any error degrades to an empty
list so an assessment never fails because a feed is down.

Note: OpenSky altitude is geometric/barometric MSL (meters); we convert to feet
and treat it as an approximate AGL proxy (no terrain subtraction yet).
"""

from __future__ import annotations

import time

import httpx

from ..config import settings
from .cache import TTLCache

STATES_URL = "https://opensky-network.org/api/states/all"
TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/"
    "protocol/openid-connect/token"
)
M_TO_FT = 3.28084

_cache = TTLCache(ttl_seconds=10)
_token: dict[str, float | str | None] = {"value": None, "exp": 0.0}


async def _bearer(client: httpx.AsyncClient) -> str | None:
    if not (settings.opensky_client_id and settings.opensky_client_secret):
        return None
    if _token["value"] and time.time() < float(_token["exp"]) - 30:
        return str(_token["value"])
    resp = await client.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.opensky_client_id,
            "client_secret": settings.opensky_client_secret,
        },
    )
    resp.raise_for_status()
    payload = resp.json()
    _token["value"] = payload["access_token"]
    _token["exp"] = time.time() + float(payload.get("expires_in", 1800))
    return str(_token["value"])


def _parse_states(raw: dict) -> list[dict]:
    out: list[dict] = []
    for s in raw.get("states") or []:
        lon, lat = s[5], s[6]
        if lat is None or lon is None:
            continue
        alt_m = s[13] if s[13] is not None else s[7]  # geo_altitude, else baro
        out.append(
            {
                "icao24": s[0],
                "callsign": (s[1] or "").strip() or None,
                "lat": lat,
                "lon": lon,
                "alt_ft": round(alt_m * M_TO_FT) if alt_m is not None else None,
                "on_ground": bool(s[8]),
                "track": s[10],
            }
        )
    return out


async def fetch_aircraft(lamin: float, lomin: float, lamax: float, lomax: float) -> list[dict]:
    key = f"{lamin:.2f},{lomin:.2f},{lamax:.2f},{lomax:.2f}"
    cached = _cache.get(key)
    if cached is not None:
        return cached

    params = {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            headers = {}
            token = await _bearer(client)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            resp = await client.get(STATES_URL, params=params, headers=headers)
            resp.raise_for_status()
            aircraft = _parse_states(resp.json())
    except Exception:  # noqa: BLE001 — feed outage must not break assessment
        aircraft = []

    _cache.set(key, aircraft)
    return aircraft
