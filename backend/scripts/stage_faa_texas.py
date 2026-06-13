"""Stage real FAA airspace data for the Texas pilot into backend/data/faa/.

Downloads Class B/C/D controlled airspace and Special Use Airspace (Prohibited,
Restricted, MOA, etc.) for Texas from the FAA's public ArcGIS feature services
as GeoJSON. Run occasionally to refresh; the output is committed so the app
works without network at runtime.

    python scripts/stage_faa_texas.py
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "faa"

CLASS_URL = (
    "https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/ArcGIS/rest/services/"
    "Class_Airspace/FeatureServer/0/query"
)
SUA_URL = (
    "https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/ArcGIS/rest/services/"
    "Special_Use_Airspace/FeatureServer/0/query"
)

CLASS_FIELDS = "IDENT,NAME,CLASS,LOCAL_TYPE,LOWER_VAL,LOWER_UOM,UPPER_VAL,UPPER_UOM,CITY"
SUA_FIELDS = "NAME,TYPE_CODE,CLASS,LOWER_VAL,LOWER_UOM,UPPER_VAL,UPPER_UOM,CITY"


def _fetch(url: str, where: str, fields: str) -> dict:
    """Page through an ArcGIS layer and return one merged GeoJSON FeatureCollection."""
    features: list[dict] = []
    offset = 0
    page = 2000
    with httpx.Client(timeout=60) as client:
        while True:
            params = {
                "where": where,
                "outFields": fields,
                "f": "geojson",
                "outSR": "4326",
                "geometryPrecision": "4",  # ~11 m; plenty for airspace polygons
                "resultOffset": offset,
                "resultRecordCount": page,
            }
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            chunk = data.get("features", [])
            features.extend(chunk)
            if len(chunk) < page:
                break
            offset += page
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading TX Class B/C/D airspace…")
    cls = _fetch(CLASS_URL, "STATE='TX' AND CLASS IN ('B','C','D')", CLASS_FIELDS)
    (OUT_DIR / "class_airspace_tx.geojson").write_text(json.dumps(cls), encoding="utf-8")
    print(f"  {len(cls['features'])} features -> class_airspace_tx.geojson")

    print("Downloading TX Special Use Airspace…")
    sua = _fetch(SUA_URL, "STATE='TX'", SUA_FIELDS)
    (OUT_DIR / "sua_tx.geojson").write_text(json.dumps(sua), encoding="utf-8")
    print(f"  {len(sua['features'])} features -> sua_tx.geojson")

    print("Done.")


if __name__ == "__main__":
    main()
