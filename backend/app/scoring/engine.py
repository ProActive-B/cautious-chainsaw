"""Collateral-risk scoring per countermeasure class.

Translates location attributes into a 0-100 collateral-risk score, a band, and
the top drivers, using the modeling guidance from the C-UAS research:
ballistic/debris fall-zone vs. population, RF interference radius vs. comms,
GPS area effects on aviation, and laser ocular/aviation hazard. Detection
methods carry minimal collateral risk and are scored low.

These are transparent heuristics for decision SUPPORT, not engineering models.
"""

from __future__ import annotations

from ..models import LocationAttributes, RiskScore
from ..taxonomy import Countermeasure, is_detection

_POP_FACTOR = {"high": 45, "medium": 22, "low": 8, None: 18}
_RF_FACTOR = {"high": 35, "medium": 18, "low": 6, None: 15}


def _band(value: int) -> str:
    if value >= 67:
        return "high"
    if value >= 34:
        return "medium"
    return "low"


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _airspace_deconfliction(loc: LocationAttributes) -> tuple[int, list[str]]:
    """Penalty for manned aircraft / airport proximity (kinetic & air hazards)."""
    drivers: list[str] = []
    penalty = 0
    close = [
        a
        for a in loc.nearby_aircraft
        if a.distance_nm <= 5 and (a.altitude_ft_agl is None or a.altitude_ft_agl <= 1000)
    ]
    if close:
        penalty += 30
        nearest = min(close, key=lambda a: a.distance_nm)
        alt = f"@ {int(nearest.altitude_ft_agl)} ft" if nearest.altitude_ft_agl else ""
        drivers.append(f"manned aircraft {nearest.distance_nm:.1f} nm {alt}".strip())
    if loc.nearest_airport_distance_nm is not None and loc.nearest_airport_distance_nm < 5:
        penalty += 15
        drivers.append(f"within {loc.nearest_airport_distance_nm:.1f} nm of {loc.nearest_airport}")
    if loc.active_tfr:
        penalty += 10
        drivers.append("active TFR over location")
    return penalty, drivers


def _pop_band(loc: LocationAttributes) -> str | None:
    """Population band drives debris-to-people risk (people on the ground)."""
    d = loc.population_density_per_km2
    if d is None:
        return None
    if d >= 1000:
        return "high"
    if d >= 300:
        return "medium"
    return "low"


def score(cm: Countermeasure, loc: LocationAttributes) -> RiskScore:
    pop = _pop_band(loc)  # debris risk scales with population density, not building count
    rf = loc.rf_congestion
    air_pen, air_drivers = _airspace_deconfliction(loc)

    drivers: list[str] = []
    value = 0.0

    if is_detection(cm):
        # Minimal collateral; small bump for radar near airports (interference).
        value = 12
        if cm == Countermeasure.RADAR and loc.nearest_airport_distance_nm is not None and (
            loc.nearest_airport_distance_nm < 5
        ):
            value += 12
            drivers.append("radar frequency coordination near airport")
        else:
            drivers.append("passive / minimal collateral")
        return RiskScore(value=_clamp(value), band=_band(_clamp(value)), drivers=drivers)

    if cm in (Countermeasure.KINETIC, Countermeasure.NET_CAPTURE, Countermeasure.INTERCEPTOR_DRONE):
        base = {"kinetic": 1.0, "net_capture": 0.5, "interceptor_drone": 0.65}[cm.value]
        pop_component = _POP_FACTOR[pop] * (1.6 if cm == Countermeasure.KINETIC else 1.0)
        value = pop_component + air_pen
        drivers.append(f"{pop or 'unknown'}-density area (falling-debris/ballistic fall zone)")
        drivers.extend(air_drivers)
        value *= base + 0.4  # net/interceptor lower than kinetic for same setting
        if cm == Countermeasure.KINETIC:
            drivers.append("stray-projectile hazard")

    elif cm in (Countermeasure.RF_JAMMING, Countermeasure.HPM):
        value = _RF_FACTOR[rf] + _POP_FACTOR[pop] * 0.5 + air_pen * 0.6
        drivers.append(f"{rf or 'unknown'} RF congestion (cellular/Wi-Fi/GPS/public-safety overlap)")
        if cm == Countermeasure.HPM:
            value += 15
            drivers.append("area electronics-damage cone")
        drivers.extend(air_drivers)

    elif cm == Countermeasure.GNSS_JAM_SPOOF:
        value = 78 + air_pen * 0.4  # near-always-high: aviation/timing area effects
        drivers.append("uncontainable GPS area effects on aviation, timing, emergency services")
        drivers.extend(air_drivers)

    elif cm == Countermeasure.HEL:
        value = 55 + air_pen
        drivers.append("ocular hazard (NOHD) + aviation flash/dazzle along beam path")
        drivers.extend(air_drivers)

    elif cm == Countermeasure.PROTOCOL_TAKEOVER:
        value = 25 + air_pen * 0.7
        drivers.append("safe-landing zone must be deconflicted; failed takeover = uncontrolled descent")
        drivers.extend(air_drivers)

    else:  # pragma: no cover — all classes covered above
        value = 40
        drivers.append("default risk estimate")

    val = _clamp(value)
    # Keep the 3 most salient drivers.
    return RiskScore(value=val, band=_band(val), drivers=drivers[:3])
