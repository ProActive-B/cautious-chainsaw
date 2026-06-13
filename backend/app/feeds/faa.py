"""Real FAA airspace lookups over the staged Texas GeoJSON.

Loads Class B/C/D and Special Use Airspace polygons (backend/data/faa/) once and
answers point-in-polygon / nearest-airspace queries with shapely. If the staged
files are absent (fresh checkout that hasn't run scripts/stage_faa_texas.py),
every function returns "no data" so callers fall back to the seed circles.
"""

from __future__ import annotations

import functools
import json
import math
import warnings
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from ..config import settings

# Most-controlled first — used to pick the governing class when rings overlap.
_CLASS_PRIORITY = {"B": 0, "C": 1, "D": 2, "E": 3}


@functools.lru_cache(maxsize=1)
def _class_airspace() -> list[tuple[dict, BaseGeometry]]:
    return _load("class_airspace_tx.geojson")


@functools.lru_cache(maxsize=1)
def _sua() -> list[tuple[dict, BaseGeometry]]:
    return _load("sua_tx.geojson")


def _load(filename: str) -> list[tuple[dict, BaseGeometry]]:
    path: Path = settings.data_dir / "faa" / filename
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[tuple[dict, BaseGeometry]] = []
    for feat in data.get("features", []):
        geom = feat.get("geometry")
        if not geom:
            continue
        g = shape(geom)
        if not g.is_valid:
            g = g.buffer(0)  # repair self-intersections so contains/distance are sound
        if g.is_empty:
            continue
        out.append((feat.get("properties", {}), g))
    return out


def has_data() -> bool:
    return bool(_class_airspace())


def airspace_at(lat: float, lon: float) -> dict | None:
    """Governing controlled airspace at the point, or None if uncontrolled/no data."""
    pt = Point(lon, lat)
    hits = [props for props, geom in _class_airspace() if geom.contains(pt)]
    if not hits:
        return None
    hits.sort(key=lambda p: _CLASS_PRIORITY.get(p.get("CLASS", "E"), 9))
    p = hits[0]
    return {
        "class": p.get("CLASS"),
        "name": (p.get("NAME") or "").title() or None,
        "lower_ft": _as_int(p.get("LOWER_VAL")),
        "upper_ft": _as_int(p.get("UPPER_VAL")),
    }


def nearest_controlled(lat: float, lon: float) -> tuple[str, float] | None:
    """Nearest Class B/C/D airspace name + approx distance (nm)."""
    data = _class_airspace()
    if not data:
        return None
    scale = math.cos(math.radians(lat))
    pt = Point(lon * scale, lat)
    best_name, best_deg = None, None
    with warnings.catch_warnings():
        # A few FAA polygons yield NaN distance even after repair; skip them quietly.
        warnings.simplefilter("ignore", RuntimeWarning)
        for props, geom in data:
            # Scale longitude so planar distance ~ degrees of latitude.
            d = pt.distance(_scaled(geom, scale))
            if not math.isfinite(d):
                continue
            if best_deg is None or d < best_deg:
                best_deg = d
                best_name = (props.get("NAME") or "").title() or None
    if best_name is None or best_deg is None:
        return None
    return best_name, round(best_deg * 60.0, 1)  # 1 deg lat ~ 60 nm


def sua_at(lat: float, lon: float) -> list[dict]:
    """Special-use airspace (Prohibited/Restricted/MOA/etc.) containing the point."""
    pt = Point(lon, lat)
    return [
        {"name": (props.get("NAME") or "").title(), "type": props.get("TYPE_CODE")}
        for props, geom in _sua()
        if geom.contains(pt)
    ]


def _scaled(geom: BaseGeometry, scale: float) -> BaseGeometry:
    from shapely.affinity import scale as affine_scale

    # Scale x (lon) about the origin so distances approximate latitude degrees.
    return affine_scale(geom, xfact=scale, yfact=1.0, origin=(0, 0))


def _as_int(v) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None
