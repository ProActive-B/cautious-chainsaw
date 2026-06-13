"""Reproduce /api/assess through the FULL request cycle (incl. response_model)."""

import traceback

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)
body = {"profile": "federal_124n", "lat": 32.8998, "lon": -97.0403, "credible_threat": True}

try:
    r = client.post("/api/assess", json=body)
    print("status:", r.status_code)
    if r.status_code == 200:
        j = r.json()
        print("nearby_aircraft:", len(j["location"]["nearby_aircraft"]))
        print("conditional:", len(j["conditional"]))
    else:
        print("body:", r.text[:500])
except Exception:
    traceback.print_exc()
