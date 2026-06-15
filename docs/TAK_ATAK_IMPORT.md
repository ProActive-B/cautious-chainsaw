# Review CUAS assessments in ATAK (Android)

The app exports an assessment as a **TAK data package** — a `.zip` ATAK imports as
a map marker whose remarks carry the full decision (permitted / conditional /
prohibited, location, rules-DB version, disclaimer). This is a **snapshot** at
export time; live streaming would need a TAK Server.

## 1. Install ATAK
- Google Play → search **"ATAK-CIV"** (Android Team Awareness Kit, civilian build,
  by TAK Product Center) → Install.
- Open it, accept the user agreement, and grant location/storage permissions.

## 2. Get the data package onto the phone
Pick either:
- **Scan the QR code** shown under "Export to TAK" in the app's report panel with
  your phone camera. It opens a link that downloads `cuas-assessment.zip`.
- **Or** open **https://cuas-decision-map.onrender.com** on the phone, choose your
  profile, tap a location, then tap **⤓ Export to TAK** to download the `.zip`.

## 3. Import into ATAK
- **Import Manager:** ATAK toolbar → **⋮ / menu** → **Import Manager** →
  **Local SD** → browse to **Download/cuas-assessment.zip** → select. ATAK ingests
  the package and drops the marker.
- **Or "Open with":** in the phone's Files/Downloads, tap `cuas-assessment.zip` →
  **Open with ATAK** if offered.

## 4. Review
- The assessed location appears as a **marker** on the map.
- Tap it → the bubble/details show the **decision summary in the remarks**.
- Long-press the marker → delete to remove it.

## Notes
- **Snapshot only.** Re-export after changing the profile or location to refresh.
- **Live aircraft / streaming** uses a different path — point a TAK Server at the
  CoT feed (`GET /api/cot/aircraft`, `POST /api/cot/assessment`). Ask to set that up.
- ATAK-CIV is the correct civilian build; the gov/mil build is CAC-gated.
