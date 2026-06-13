"""FastAPI entrypoint for the CUAS Decision Map API."""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import settings
from .feeds import faa, notam, opensky
from .models import AssessRequest, DecisionReport
from .report import build_report
from .rules.loader import load_rules
from .spatial.attributes import gather
from .spatial.layers import build_layers
from .spatial.seed import load_seed
from .taxonomy import COUNTERMEASURE_LABELS, PROFILE_LABELS

app = FastAPI(title=settings.app_name, version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bounding-box half-size (degrees) used to fetch live aircraft around a point.
_ASSESS_BOX = 0.25


@app.get("/health")
def health() -> dict:
    rules = load_rules()
    return {
        "status": "ok",
        "version": __version__,
        "rules_loaded": len(rules),
        "rules_db_version": settings.rules_db_version,
        "feeds": {
            "faa_airspace_staged": faa.has_data(),
            "opensky_authenticated": bool(settings.opensky_client_id),
            "tfr_configured": bool(settings.faa_notam_api_key),
        },
    }


@app.get("/api/meta")
def meta() -> dict:
    return {
        "profiles": [{"id": k, "label": v} for k, v in PROFILE_LABELS.items()],
        "countermeasures": [{"id": k, "label": v} for k, v in COUNTERMEASURE_LABELS.items()],
        "default_view": load_seed().get("default_view", {"lat": 32.85, "lon": -96.85, "zoom": 9}),
        "rules_db_version": settings.rules_db_version,
    }


@app.get("/api/layers")
def layers() -> dict:
    return build_layers()


@app.get("/api/aircraft")
async def aircraft(
    lamin: float = Query(...), lomin: float = Query(...),
    lamax: float = Query(...), lomax: float = Query(...),
) -> dict:
    """Live ADS-B aircraft within a bounding box (clamped to a sane size)."""
    # Clamp overly large requests to ~2° around the center to limit the feed pull.
    if lamax - lamin > 2 or lomax - lomin > 2:
        clat, clon = (lamin + lamax) / 2, (lomin + lomax) / 2
        lamin, lamax, lomin, lomax = clat - 1, clat + 1, clon - 1, clon + 1
    data = await opensky.fetch_aircraft(lamin, lomin, lamax, lomax)
    return {"count": len(data), "aircraft": data}


@app.get("/api/_debug/opensky")
async def debug_opensky() -> dict:
    """Diagnostics for the live aircraft feed (no secrets) — why is it empty?"""
    await opensky.fetch_aircraft(32.6, -97.2, 33.1, -96.5, use_cache=False)
    return opensky.last_status


@app.post("/api/assess", response_model=DecisionReport)
async def assess(req: AssessRequest) -> DecisionReport:
    """Core endpoint: location + profile -> decision report (with live feeds)."""
    bbox = (req.lat - _ASSESS_BOX, req.lon - _ASSESS_BOX, req.lat + _ASSESS_BOX, req.lon + _ASSESS_BOX)
    air = await opensky.fetch_aircraft(*bbox)
    tfr = await notam.fetch_tfrs(*bbox)
    loc = gather(req.lat, req.lon, aircraft=air, tfr_result=tfr)
    return build_report(req, loc)


# Serve the built frontend as a single service (registered LAST so /api and
# /health take precedence). No-op in dev when dist isn't built.
if settings.frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(settings.frontend_dist), html=True), name="frontend")
