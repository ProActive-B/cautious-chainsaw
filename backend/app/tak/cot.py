"""Cursor-on-Target (CoT) XML generation for TAK (ATAK/WinTAK).

Builds CoT events for (a) an assessed location — a map marker carrying the
decision summary in its remarks — and (b) live ADS-B aircraft tracks. CoT is the
lingua franca of the TAK ecosystem; these can be pushed to a TAK Server or
bundled into a data package (see datapackage.py) for file import.
"""

from __future__ import annotations

import datetime as _dt
from xml.sax.saxutils import escape, quoteattr

from ..models import DecisionReport

FT_TO_M = 0.3048


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _fmt(dt: _dt.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _event(
    uid: str, cot_type: str, lat: float, lon: float, hae: float,
    detail: str, stale_seconds: int, how: str = "m-g",
) -> str:
    now = _now()
    stale = now + _dt.timedelta(seconds=stale_seconds)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<event version="2.0" uid={quoteattr(uid)} type={quoteattr(cot_type)} '
        f'how={quoteattr(how)} time="{_fmt(now)}" start="{_fmt(now)}" stale="{_fmt(stale)}">'
        f'<point lat="{lat:.6f}" lon="{lon:.6f}" hae="{hae:.1f}" ce="9999999.0" le="9999999.0"/>'
        f"<detail>{detail}</detail>"
        "</event>"
    )


def assessment_remarks(report: DecisionReport) -> str:
    loc = report.location
    perm = ", ".join(a.label for a in report.permitted) or "none"
    cond = ", ".join(a.label for a in report.conditional) or "none"
    proh = ", ".join(a.label for a in report.prohibited) or "none"
    lines = [
        f"CUAS Decision Map — {report.profile_label}",
        report.authority_banner,
        f"PERMITTED: {perm}",
        f"CONDITIONAL: {cond}",
        f"PROHIBITED: {proh}",
        f"Location: {loc.place_label}; airspace {loc.airspace_class}; "
        f"pop {loc.population_density_per_km2}/km2; terrain {loc.terrain} "
        f"{loc.elevation_m}m; {len(loc.nearby_aircraft)} aircraft nearby",
        f"Rules DB {report.rules_db_version} | {report.generated_as_of}",
        "DECISION SUPPORT ONLY — NOT AUTHORIZATION. Verify with counsel.",
    ]
    return "\n".join(lines)


def assessment_cot(report: DecisionReport, uid: str = "CUAS.ASSESSMENT") -> str:
    """A TAK map marker at the assessed point carrying the decision in remarks."""
    loc = report.location
    hae = (loc.elevation_m or 0.0)
    detail = (
        '<contact callsign="CUAS Assessment"/>'
        '<color argb="-1"/>'
        f"<remarks>{escape(assessment_remarks(report))}</remarks>"
    )
    # b-m-p-s-m = generic map spot marker.
    return _event(uid, "b-m-p-s-m", loc.lat, loc.lon, hae, detail, stale_seconds=3600, how="h-g-i-g-o")


def aircraft_cot(ac: dict) -> str:
    """A CoT air track for one ADS-B aircraft (neutral civil fixed-wing)."""
    callsign = ac.get("callsign") or ac.get("icao24") or "UNKNOWN"
    hae = (ac.get("alt_ft") or 0) * FT_TO_M
    track = ac.get("track")
    track_xml = f'<track course="{float(track):.1f}" speed="0.0"/>' if track is not None else ""
    detail = f"<contact callsign={quoteattr(str(callsign))}/>{track_xml}"
    uid = f"ADSB.{ac.get('icao24') or callsign}"
    return _event(uid, "a-n-A-C-F", ac["lat"], ac["lon"], hae, detail, stale_seconds=60)


def aircraft_feed_cot(aircraft: list[dict]) -> str:
    """A stream of CoT events (one per aircraft) for TAK-Server-style ingestion."""
    events = [
        aircraft_cot(a)
        for a in aircraft
        if not a.get("on_ground") and a.get("lat") is not None and a.get("lon") is not None
    ]
    return "\n".join(events)
