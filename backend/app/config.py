"""Application settings.

Values can be overridden via environment variables or a local .env file
(e.g. OPENSKY_CLIENT_ID, FAA_NOTAM_API_KEY). Secrets never live in code.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CUAS Decision Map API"
    # The rules DB version is surfaced in every decision report footer.
    rules_db_version: str = "2026.06-mvp"

    # Paths
    rules_dir: Path = BACKEND_ROOT / "rules"
    data_dir: Path = BACKEND_ROOT / "data"
    # Built frontend (Vite dist). When present, FastAPI serves it at "/" so the
    # whole app is a single deployable service. Absent in pure-dev (Vite proxy).
    frontend_dist: Path = BACKEND_ROOT.parent / "frontend" / "dist"

    # CORS — local Vite dev server by default.
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # External feed credentials (Phase 2; optional in MVP).
    faa_notam_api_key: str | None = None
    opensky_client_id: str | None = None
    opensky_client_secret: str | None = None


settings = Settings()
