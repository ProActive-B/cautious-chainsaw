"""Pydantic schemas for rules, requests, location attributes, and the report.

These models double as validation for the YAML rule files (Rule / Citation /
Exception) and as the API contract for the frontend (AssessRequest /
DecisionReport).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .taxonomy import Countermeasure, Profile

Effect = Literal["permitted", "conditional", "prohibited"]
RiskBand = Literal["low", "medium", "high", "n/a"]


# --------------------------------------------------------------------------- #
# Rule schema (mirrors the YAML files)
# --------------------------------------------------------------------------- #
class Citation(BaseModel):
    statute: str
    source_url: str
    advisory: Optional[str] = None


class RuleException(BaseModel):
    """A profile-specific override of a rule's base effect."""

    profile: Profile
    effect: Effect
    conditions: list[str] = Field(default_factory=list)
    note: Optional[str] = None


class Rule(BaseModel):
    id: str
    countermeasure: Countermeasure
    jurisdiction: Literal["federal", "texas"]
    applies_to_profiles: list[Profile]
    effect: Effect
    citation: Citation
    rationale: str
    exceptions: list[RuleException] = Field(default_factory=list)
    # Location predicate (optional): rule only fires when the location has
    # this attribute flag set true (e.g. "critical_infrastructure_zone").
    requires_location_flag: Optional[str] = None
    as_of: str
    review_owner: str = "counsel"


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #
class AssessRequest(BaseModel):
    profile: Profile
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    # Optional declared threat context (affects conditional authorities).
    credible_threat: bool = False


# --------------------------------------------------------------------------- #
# Location attributes (output of the spatial layer)
# --------------------------------------------------------------------------- #
class NearbyAircraft(BaseModel):
    # icao24 is optional: some community-feed targets (TIS-B/MLAT) lack a hex id.
    icao24: Optional[str] = None
    callsign: Optional[str] = None
    distance_nm: float
    altitude_ft_agl: Optional[float] = None


class LocationAttributes(BaseModel):
    lat: float
    lon: float
    place_label: str = "Unknown location"
    airspace_class: Optional[str] = None          # "B", "C", "D", "E", "G"
    uasfm_ceiling_ft: Optional[int] = None
    nearest_airport: Optional[str] = None
    nearest_airport_distance_nm: Optional[float] = None
    population_density_per_km2: Optional[float] = None
    building_density: Optional[Literal["low", "medium", "high"]] = None
    building_count: Optional[int] = None
    rf_congestion: Optional[Literal["low", "medium", "high"]] = None
    # Boolean zone flags (drive requires_location_flag rules).
    location_flags: dict[str, bool] = Field(default_factory=dict)
    active_tfr: bool = False
    active_tfr_names: list[str] = Field(default_factory=list)
    nearby_aircraft: list[NearbyAircraft] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Decision report
# --------------------------------------------------------------------------- #
class RiskScore(BaseModel):
    value: int = Field(..., ge=0, le=100)
    band: RiskBand
    drivers: list[str] = Field(default_factory=list)


class CountermeasureAssessment(BaseModel):
    countermeasure: Countermeasure
    label: str
    category: Literal["detection", "mitigation"]
    effect: Effect
    rationale: str
    citations: list[Citation] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    risk: Optional[RiskScore] = None


class DocumentationPathway(BaseModel):
    title: str
    why: str
    where_to_submit: str
    url: str
    draft_available: bool = False


class DecisionReport(BaseModel):
    profile: Profile
    profile_label: str
    location: LocationAttributes
    authority_banner: str
    permitted: list[CountermeasureAssessment]
    conditional: list[CountermeasureAssessment]
    prohibited: list[CountermeasureAssessment]
    documentation: list[DocumentationPathway]
    # Footer / provenance
    rules_db_version: str
    generated_as_of: str
    disclaimer: str
