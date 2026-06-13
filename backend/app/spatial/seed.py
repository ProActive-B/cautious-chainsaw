"""Load the pilot staging data and provide geo helpers.

MVP uses center+radius definitions (data/seed/tx_pilot.json) rather than full
GIS layers; this keeps the attribute logic and the map layers driven by one
source of truth that swaps cleanly for real FAA/Census/HIFLD data in Phase 2.
"""

from __future__ import annotations

import functools
import json
import math
from pathlib import Path

from ..config import settings

EARTH_RADIUS_NM = 3440.065  # nautical miles


@functools.lru_cache(maxsize=1)
def load_seed() -> dict:
    path: Path = settings.data_dir / "seed" / "tx_pilot.json"
    return json.loads(path.read_text(encoding="utf-8"))


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.asin(min(1.0, math.sqrt(a)))


def geodesic_circle(lat: float, lon: float, radius_nm: float, n: int = 48) -> list[list[float]]:
    """Return a closed ring of [lon, lat] points approximating a circle.

    Used to render center+radius seed definitions as GeoJSON polygons.
    """
    ring: list[list[float]] = []
    ang_dist = radius_nm / EARTH_RADIUS_NM
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    for i in range(n + 1):
        brng = 2 * math.pi * (i / n)
        lat2 = math.asin(
            math.sin(lat1) * math.cos(ang_dist)
            + math.cos(lat1) * math.sin(ang_dist) * math.cos(brng)
        )
        lon2 = lon1 + math.atan2(
            math.sin(brng) * math.sin(ang_dist) * math.cos(lat1),
            math.cos(ang_dist) - math.sin(lat1) * math.sin(lat2),
        )
        ring.append([math.degrees(lon2), math.degrees(lat2)])
    return ring
