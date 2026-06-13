"""FastAPI entrypoint for the CUAS Decision Map API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import settings
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


@app.get("/health")
def health() -> dict:
    # Loading rules here also surfaces any YAML errors at first request.
    rules = load_rules()
    return {"status": "ok", "version": __version__, "rules_loaded": len(rules),
            "rules_db_version": settings.rules_db_version}


@app.get("/api/meta")
def meta() -> dict:
    """Vocabularies + default map view for the frontend."""
    return {
        "profiles": [{"id": k, "label": v} for k, v in PROFILE_LABELS.items()],
        "countermeasures": [{"id": k, "label": v} for k, v in COUNTERMEASURE_LABELS.items()],
        "default_view": load_seed().get("default_view", {"lat": 32.85, "lon": -96.85, "zoom": 9}),
        "rules_db_version": settings.rules_db_version,
    }


@app.get("/api/layers")
def layers() -> dict:
    """GeoJSON layers for the map (sample pilot staging data)."""
    return build_layers()


@app.post("/api/assess", response_model=DecisionReport)
def assess(req: AssessRequest) -> DecisionReport:
    """Core endpoint: location + profile -> decision report."""
    loc = gather(req.lat, req.lon)
    return build_report(req, loc)


# Serve the built frontend as a single service (registered LAST so the /api and
# /health routes above take precedence). No-op in dev when dist isn't built.
if settings.frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(settings.frontend_dist), html=True), name="frontend")
