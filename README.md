# CUAS Decision Map

A map-based **decision-support** tool that, for a clicked location and a chosen
authority profile, produces a decision report: which counter-UAS countermeasures
are **permitted / conditional / prohibited** (with legal citations), a
collateral-**risk score** for each actionable option, and the
**documentation/coordination pathway** to pursue when you can't act yourself.

> ⚠️ **DECISION SUPPORT ONLY — NOT LEGAL ADVICE OR AUTHORIZATION.** C-UAS
> mitigation by unauthorized parties can be a federal crime. The rules database
> is advisory, perishable, and has **not** been reviewed by counsel. Verify with
> counsel and coordinate with federal authorities before any action.
> See [docs/SOURCES.md](docs/SOURCES.md).

## Status
- ✅ Rules engine + cited YAML legal DB (federal + Texas), most-restrictive-wins
- ✅ Authority-profile master filter (7 profiles)
- ✅ Collateral risk scoring (debris/RF/GPS/laser/aviation-deconfliction)
- ✅ Documentation pathway generator
- ✅ React + MapLibre frontend (click-to-assess, layer toggles)
- ✅ **Phase 2 — live feeds & real airspace:** live ADS-B aircraft (OpenSky) feed
  overhead-traffic into the risk score; **real FAA Class B/C/D + Special Use
  Airspace** for Texas drive the authoritative airspace class. TFR/NOTAM client
  is wired but key-gated (set `FAA_NOTAM_API_KEY`). Population/buildings/terrain
  and bespoke zones are still **sample** data — next to replace.
- ⏳ **Phase 4:** TAK (ATAK/WinTAK) export; offline/on-prem bundles

Refresh the staged FAA airspace anytime: `python backend/scripts/stage_faa_texas.py`.

Pilot scope: **Texas** (federal + Tex. Gov't Code ch. 423), sample data centered
on the Dallas–Fort Worth area.

## Architecture
- **Backend** — Python / FastAPI. Rules engine (`app/rules`), risk scoring
  (`app/scoring`), spatial attributes (`app/spatial`), documentation pathways
  (`app/docs`). Legal rules live as cited YAML under `backend/rules/`.
- **Frontend** — React + TypeScript + Vite + MapLibre GL JS. Calls `/api/*`.

## Run it

### Backend (port 8000)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir .
# health: http://localhost:8000/health   · docs: http://localhost:8000/docs
```

### Frontend (port 5173, proxies /api to :8000)
```powershell
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

### Tests
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

## Deploy (demo)

The app ships as a **single service**: `npm run build` produces the frontend,
and FastAPI serves it at `/` alongside the API at `/api`. One image, one URL,
no CORS.

```powershell
# Build the image and run it locally
docker build -t cuas-decision-map .
docker run -p 8000:8000 cuas-decision-map   # open http://localhost:8000
```

**Render (fastest shareable URL):** push to GitHub, then in Render choose
*New → Blueprint* and point it at this repo — [render.yaml](render.yaml) defines
the service. Fly.io and Railway work with the same [Dockerfile](Dockerfile).
Phase-2 feed secrets (`FAA_NOTAM_API_KEY`, `OPENSKY_*`) go in the host's
dashboard, never in the repo.

**Push to GitHub** (create an empty private repo first):
```powershell
git remote add origin https://github.com/<you>/cuas-decision-map.git
git push -u origin main
```
Then enable branch protection + required Code Owner review on `main` so changes
under `backend/rules/**` require counsel/SME sign-off (see [.github/CODEOWNERS](.github/CODEOWNERS)).

## How a decision is made
1. Pick an **authority profile** (e.g. private security, CI owner, federal §124n,
   certified SLTT). This is the master filter.
2. **Click a location.** The backend gathers attributes (airspace, nearest
   airport, population/RF bands, zone flags) and runs the rules engine.
3. The **decision report** ranks permitted/conditional options by collateral
   risk, lists prohibited ones with the controlling statute, and offers the
   filing/coordination pathway.

## Editing the law
Rules are data: `backend/rules/federal/*.yaml` and `backend/rules/texas/*.yaml`.
Each rule carries its citation, rationale, `as_of` date, and `review_owner`.
Edit YAML and restart (or call `reload_rules()`); no code change required.
