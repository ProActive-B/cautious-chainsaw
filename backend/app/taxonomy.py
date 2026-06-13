"""Controlled vocabularies shared across the rules engine, scoring, and API.

These enums are the single source of truth for countermeasure classes and
authority profiles. Rule YAML files and risk-scoring modules reference these
exact string values, so changes here ripple everywhere intentionally.
"""

from __future__ import annotations

from enum import Enum


class Profile(str, Enum):
    """Authority profile — the master filter for the whole decision.

    Who the operator is determines what the law lets them do, before any
    location-specific analysis. Values are stable identifiers used in rule YAML.
    """

    FEDERAL_124N = "federal_124n"            # DHS / DOJ covered facilities (6 U.S.C. 124n)
    DOD_130I = "dod_130i"                    # DoD covered installations (10 U.S.C. 130i)
    DOE_NNSA = "doe_nnsa"                    # DOE/NNSA nuclear security (FY2026 NDAA 3111)
    STATE_LOCAL_LE_CERTIFIED = "state_local_le_certified"      # SAFER SKIES certified
    STATE_LOCAL_LE_UNCERTIFIED = "state_local_le_uncertified"  # not (yet) certified
    CI_OWNER = "ci_owner"                    # critical-infrastructure owner/operator
    PRIVATE_SECURITY = "private_security"    # private security / other private party


PROFILE_LABELS: dict[str, str] = {
    Profile.FEDERAL_124N: "Federal — DHS/DOJ (6 U.S.C. § 124n)",
    Profile.DOD_130I: "Federal — DoD (10 U.S.C. § 130i)",
    Profile.DOE_NNSA: "Federal — DOE/NNSA (FY2026 NDAA § 3111)",
    Profile.STATE_LOCAL_LE_CERTIFIED: "State/Local LE — certified (SAFER SKIES)",
    Profile.STATE_LOCAL_LE_UNCERTIFIED: "State/Local LE — not certified",
    Profile.CI_OWNER: "Critical-infrastructure owner/operator",
    Profile.PRIVATE_SECURITY: "Private security / private party",
}


class Countermeasure(str, Enum):
    """C-UAS countermeasure classes from the taxonomy research.

    Split into DETECTION (generally more permissible) and MITIGATION
    (heavily restricted). Used as rule keys and scoring-model selectors.
    """

    # --- Detection (generally permissible) ---
    RF_DETECTION = "rf_detection"
    RADAR = "radar"
    EO_IR = "eo_ir"
    ACOUSTIC = "acoustic"

    # --- Mitigation (heavily restricted) ---
    RF_JAMMING = "rf_jamming"
    GNSS_JAM_SPOOF = "gnss_jam_spoof"
    PROTOCOL_TAKEOVER = "protocol_takeover"
    KINETIC = "kinetic"
    NET_CAPTURE = "net_capture"
    INTERCEPTOR_DRONE = "interceptor_drone"
    HPM = "hpm"
    HEL = "hel"


DETECTION_CLASSES: frozenset[str] = frozenset(
    {
        Countermeasure.RF_DETECTION,
        Countermeasure.RADAR,
        Countermeasure.EO_IR,
        Countermeasure.ACOUSTIC,
    }
)

MITIGATION_CLASSES: frozenset[str] = frozenset(
    {
        Countermeasure.RF_JAMMING,
        Countermeasure.GNSS_JAM_SPOOF,
        Countermeasure.PROTOCOL_TAKEOVER,
        Countermeasure.KINETIC,
        Countermeasure.NET_CAPTURE,
        Countermeasure.INTERCEPTOR_DRONE,
        Countermeasure.HPM,
        Countermeasure.HEL,
    }
)


COUNTERMEASURE_LABELS: dict[str, str] = {
    Countermeasure.RF_DETECTION: "RF detection / direction-finding",
    Countermeasure.RADAR: "Radar",
    Countermeasure.EO_IR: "Electro-optical / infrared (EO/IR)",
    Countermeasure.ACOUSTIC: "Acoustic detection",
    Countermeasure.RF_JAMMING: "RF jamming / disruption",
    Countermeasure.GNSS_JAM_SPOOF: "GNSS/GPS jamming or spoofing",
    Countermeasure.PROTOCOL_TAKEOVER: "Protocol takeover / safe-landing",
    Countermeasure.KINETIC: "Kinetic (projectiles / firearms)",
    Countermeasure.NET_CAPTURE: "Net capture (net gun)",
    Countermeasure.INTERCEPTOR_DRONE: "Interceptor / capture drone",
    Countermeasure.HPM: "High-power microwave (HPM)",
    Countermeasure.HEL: "High-energy laser (HEL)",
}


def is_detection(cm: str) -> bool:
    return cm in DETECTION_CLASSES
