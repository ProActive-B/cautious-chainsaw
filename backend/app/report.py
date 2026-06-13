"""Assemble the DecisionReport from the rules engine, scoring, and pathways."""

from __future__ import annotations

import datetime as _dt

from .config import settings
from .docs import pathways as docs_pathways
from .models import (
    AssessRequest,
    CountermeasureAssessment,
    DecisionReport,
    LocationAttributes,
)
from .rules import engine as rules_engine
from .scoring import engine as scoring_engine
from .taxonomy import (
    COUNTERMEASURE_LABELS,
    PROFILE_LABELS,
    Profile,
    is_detection,
)

DISCLAIMER = (
    "DECISION SUPPORT ONLY — NOT LEGAL ADVICE OR AUTHORIZATION. C-UAS authority and "
    "collateral-risk assessments are advisory, location- and time-sensitive, and the "
    "underlying law is changing. Verify with counsel and coordinate with federal "
    "authorities before any action. Mitigation by unauthorized parties can be a federal crime."
)

_BANNERS: dict[Profile, str] = {
    Profile.FEDERAL_124N: (
        "DHS/DOJ covered-facility authority (6 U.S.C. § 124n): detection permitted; "
        "mitigation of a credible threat permitted with FAA coordination. Confirm the "
        "facility is designated and coordination is in place."
    ),
    Profile.DOD_130I: (
        "DoD covered-installation authority (10 U.S.C. § 130i): detection permitted; "
        "mitigation of a credible threat permitted with FAA coordination."
    ),
    Profile.DOE_NNSA: (
        "DOE/NNSA nuclear-security authority (FY2026 NDAA § 3111): detection and "
        "mitigation permitted at covered NNSA facilities with FAA coordination."
    ),
    Profile.STATE_LOCAL_LE_CERTIFIED: (
        "Certified SLTT authority (SAFER SKIES): limited mitigation of credible threats "
        "with DOJ certification and real-time FAA coordination. GPS jam/spoof, HPM, and "
        "HEL remain OUTSIDE this authority. VERIFY current DOJ implementing regulations."
    ),
    Profile.STATE_LOCAL_LE_UNCERTIFIED: (
        "No mitigation authority yet. Passive detection is generally permissible. "
        "Pursue SAFER SKIES certification and report threats to federal partners."
    ),
    Profile.CI_OWNER: (
        "No mitigation authority. Passive detection is permissible (do not intercept/"
        "decode the control link — Wiretap/Pen-Trap). Mitigation is reserved to "
        "authorized federal and certified SLTT entities — see the documentation pathway."
    ),
    Profile.PRIVATE_SECURITY: (
        "No mitigation authority. Passive detection is permissible (no signal interception). "
        "Any active measure can be a federal crime — see the documentation pathway."
    ),
}


def build_report(req: AssessRequest, loc: LocationAttributes) -> DecisionReport:
    resolved = rules_engine.resolve(req.profile, loc, credible_threat=req.credible_threat)

    permitted: list[CountermeasureAssessment] = []
    conditional: list[CountermeasureAssessment] = []
    prohibited: list[CountermeasureAssessment] = []

    for cm, r in resolved.items():
        assessment = CountermeasureAssessment(
            countermeasure=cm,
            label=COUNTERMEASURE_LABELS[cm],
            category="detection" if is_detection(cm) else "mitigation",
            effect=r.effect,
            rationale=r.rationale,
            citations=r.citations,
            conditions=r.conditions,
            risk=scoring_engine.score(cm, loc) if r.effect != "prohibited" else None,
        )
        if r.effect == "permitted":
            permitted.append(assessment)
        elif r.effect == "conditional":
            conditional.append(assessment)
        else:
            prohibited.append(assessment)

    # Rank actionable options by ascending collateral risk (safest first).
    permitted.sort(key=lambda a: a.risk.value if a.risk else 0)
    conditional.sort(key=lambda a: a.risk.value if a.risk else 0)

    return DecisionReport(
        profile=req.profile,
        profile_label=PROFILE_LABELS[req.profile],
        location=loc,
        authority_banner=_BANNERS[req.profile],
        permitted=permitted,
        conditional=conditional,
        prohibited=prohibited,
        documentation=docs_pathways.generate(req.profile, loc),
        rules_db_version=settings.rules_db_version,
        generated_as_of=_dt.date.today().isoformat(),
        disclaimer=DISCLAIMER,
    )
