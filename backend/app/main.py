"""FastAPI entrypoint for the CUAS Decision Map API."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import settings
from .feeds import adsb, buildings, census, faa, notam, terrain as terrain_feed
from .tak import cot, datapackage
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
            "aircraft_provider": "adsb.lol / airplanes.live (community, keyless)",
            "population_source": "US Census ACS (live, keyless)",
            "buildings_source": "OpenStreetMap / Overpass (live, keyless)",
            "terrain_source": "USGS 3DEP (live, keyless)",
            "tfr_configured": bool(settings.faa_notam_api_key),
            "tak_export": True,
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
    data = await adsb.fetch_aircraft(lamin, lomin, lamax, lomax)
    return {"count": len(data), "aircraft": data}


@app.get("/api/_debug/aircraft")
async def debug_aircraft() -> dict:
    """Diagnostics for the live aircraft feed (which provider, status, count)."""
    await adsb.fetch_aircraft(32.6, -97.2, 33.1, -96.5, use_cache=False)
    return adsb.last_status


async def _run_assess(req: AssessRequest) -> DecisionReport:
    """Shared pipeline: fetch all live feeds concurrently and build the report."""
    bbox = (req.lat - _ASSESS_BOX, req.lon - _ASSESS_BOX, req.lat + _ASSESS_BOX, req.lon + _ASSESS_BOX)
    # Each feed fails safe to None/[] internally.
    air, tfr, pop, bld, terr = await asyncio.gather(
        adsb.fetch_aircraft(*bbox),
        notam.fetch_tfrs(*bbox),
        census.population_density(req.lat, req.lon),
        buildings.building_density(req.lat, req.lon),
        terrain_feed.terrain(req.lat, req.lon),
    )
    loc = gather(req.lat, req.lon, aircraft=air, tfr_result=tfr, population=pop, buildings=bld, terrain=terr)
    return build_report(req, loc)


@app.post("/api/assess", response_model=DecisionReport)
async def assess(req: AssessRequest) -> DecisionReport:
    """Core endpoint: location + profile -> decision report (with live feeds)."""
    return await _run_assess(req)


# --------------------------------------------------------------------------- #
# TAK (ATAK/WinTAK) export — Cursor-on-Target + data package
# --------------------------------------------------------------------------- #
@app.post("/api/cot/assessment")
async def cot_assessment(req: AssessRequest) -> Response:
    """Assessment as a CoT marker (XML) — push to a TAK Server or import."""
    report = await _run_assess(req)
    return Response(content=cot.assessment_cot(report), media_type="application/xml")


@app.post("/api/tak/datapackage")
async def tak_datapackage(req: AssessRequest) -> Response:
    """Assessment as a TAK data package (.zip) for ATAK/WinTAK file import."""
    report = await _run_assess(req)
    uid = f"CUAS.{req.lat:.4f}_{req.lon:.4f}"
    pkg = datapackage.build_package(cot.assessment_cot(report, uid=uid), uid=uid)
    return Response(
        content=pkg,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="cuas-assessment.zip"'},
    )


@app.get("/api/cot/aircraft")
async def cot_aircraft(
    lamin: float = Query(...), lomin: float = Query(...),
    lamax: float = Query(...), lomax: float = Query(...),
) -> Response:
    """Live aircraft as a CoT event stream (for TAK Server / CoT ingestion)."""
    data = await adsb.fetch_aircraft(lamin, lomin, lamax, lomax)
    return Response(content=cot.aircraft_feed_cot(data), media_type="application/xml")


# Serve the built frontend as a single service (registered LAST so /api and
# /health take precedence). No-op in dev when dist isn't built.
if settings.frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(settings.frontend_dist), html=True), name="frontend")
