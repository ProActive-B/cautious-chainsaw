"""Rules-engine, scoring, and report tests.

These encode the legal expectations the engine must preserve: unauthorized
parties cannot mitigate; federal/certified profiles get conditional authority;
detection is permissible; and the SAFER SKIES carve-outs exclude GPS/HPM/HEL.
"""

from __future__ import annotations

from app.models import AssessRequest, LocationAttributes, NearbyAircraft
from app.report import build_report
from app.rules import engine
from app.rules.loader import load_rules
from app.scoring import engine as scoring
from app.spatial.attributes import gather
from app.taxonomy import Countermeasure, Profile


def _loc(**overrides) -> LocationAttributes:
    base = dict(lat=32.95, lon=-96.65, population_density_per_km2=600,
                building_density="medium", rf_congestion="medium")
    base.update(overrides)
    return LocationAttributes(**base)


def test_rules_load_without_error():
    rules = load_rules()
    assert len(rules) > 10
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids))  # unique ids


def test_private_security_cannot_jam():
    res = engine.resolve(Profile.PRIVATE_SECURITY, _loc())
    rf = res[Countermeasure.RF_JAMMING]
    assert rf.effect == "prohibited"
    assert any("333" in c.statute for c in rf.citations)


def test_federal_124n_jam_is_conditional():
    res = engine.resolve(Profile.FEDERAL_124N, _loc())
    rf = res[Countermeasure.RF_JAMMING]
    assert rf.effect == "conditional"
    assert "faa_coordination" in rf.conditions


def test_detection_permitted_for_ci_owner():
    res = engine.resolve(Profile.CI_OWNER, _loc())
    assert res[Countermeasure.RF_DETECTION].effect == "permitted"
    assert res[Countermeasure.ACOUSTIC].effect == "permitted"


def test_certified_sltt_kinetic_conditional_but_gnss_prohibited():
    res = engine.resolve(Profile.STATE_LOCAL_LE_CERTIFIED, _loc())
    assert res[Countermeasure.KINETIC].effect == "conditional"
    assert "doj_certification" in res[Countermeasure.KINETIC].conditions
    # SAFER SKIES does NOT cover GPS jam/spoof, HPM, or HEL.
    assert res[Countermeasure.GNSS_JAM_SPOOF].effect == "prohibited"
    assert res[Countermeasure.HPM].effect == "prohibited"
    assert res[Countermeasure.HEL].effect == "prohibited"


def test_texas_citation_present_for_private():
    res = engine.resolve(Profile.PRIVATE_SECURITY, _loc())
    kinetic = res[Countermeasure.KINETIC]
    assert any("Tex" in c.statute for c in kinetic.citations)
    assert any("§ 32" in c.statute for c in kinetic.citations)


def test_credible_threat_marks_condition_satisfied():
    res = engine.resolve(Profile.FEDERAL_124N, _loc(), credible_threat=True)
    rf = res[Countermeasure.RF_JAMMING]
    assert any("declared" in c for c in rf.conditions)


# --- scoring ---
def test_kinetic_higher_risk_in_dense_area():
    high = scoring.score(Countermeasure.KINETIC, _loc(population_density_per_km2=2500))
    low = scoring.score(Countermeasure.KINETIC, _loc(population_density_per_km2=40))
    assert high.value > low.value


def test_gnss_is_high_risk():
    s = scoring.score(Countermeasure.GNSS_JAM_SPOOF, _loc(population_density_per_km2=40))
    assert s.band == "high"


def test_aircraft_overhead_raises_kinetic_risk():
    clear = scoring.score(Countermeasure.KINETIC, _loc(building_density="medium"))
    with_air = scoring.score(
        Countermeasure.KINETIC,
        _loc(building_density="medium",
             nearby_aircraft=[NearbyAircraft(icao24="abc123", distance_nm=2.1, altitude_ft_agl=600)]),
    )
    assert with_air.value > clear.value


def test_detection_is_low_collateral():
    s = scoring.score(Countermeasure.ACOUSTIC, _loc(building_density="high"))
    assert s.band == "low"


# --- full report on the pilot site ---
def test_report_private_security_at_pilot_site():
    loc = gather(32.95, -96.65)
    assert loc.location_flags.get("critical_infrastructure_zone") is True
    report = build_report(AssessRequest(profile=Profile.PRIVATE_SECURITY, lat=32.95, lon=-96.65), loc)
    assert report.permitted, "detection options should be permitted"
    assert report.prohibited, "mitigation should be prohibited"
    assert report.documentation, "a documentation pathway must be offered"
    # Detection (permitted) should be ranked safest-first and low risk.
    assert report.permitted[0].risk.band == "low"
