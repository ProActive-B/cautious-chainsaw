"""Documentation & coordination pathway generator.

When a profile cannot lawfully mitigate (the common case), the most useful
output is *what to file and where*. This builds that pathway from the profile
and location — the actionable answer to "I can't act, so now what?".
"""

from __future__ import annotations

from ..models import DocumentationPathway, LocationAttributes
from ..taxonomy import Profile

_FEDERAL = {Profile.FEDERAL_124N, Profile.DOD_130I, Profile.DOE_NNSA}

# Reusable pathway definitions.
_REPORT_FBI = DocumentationPathway(
    title="Report the incursion to the FBI / DHS",
    why="Suspected unlawful UAS activity should be reported so authorized federal teams can respond.",
    where_to_submit="Local FBI Field Office (and DHS regional office); call 911 for emergencies.",
    url="https://www.fbi.gov/contact-us/field-offices",
)
_FAA_2209 = DocumentationPathway(
    title="Petition for a fixed-site flight restriction (FAA § 2209 / proposed Part 74)",
    why="Establishes a UAS no-fly designation over your facility. Note: it restricts who may fly — it does NOT grant you mitigation authority.",
    where_to_submit="FAA — Part 74 rulemaking (NPRM comments closed 2026-07-06; track final rule).",
    url="https://www.federalregister.gov/documents/2026/05/06/2026-08943/designation-restrict-the-operation-of-unmanned-aircraft-in-close-proximity-to-a-fixed-site-facility",
    draft_available=True,
)
_FAA_997 = DocumentationPathway(
    title="Request a § 99.7 Special Security Instruction / NSUFR",
    why="For national-security-sensitive sites, creates UAS flight restrictions via the sponsoring federal agency.",
    where_to_submit="Through your sponsoring federal security agency (DoD/DHS) to FAA.",
    url="https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-99/subpart-A/section-99.7.html",
)
_FEMA_GRANT = DocumentationPathway(
    title="Apply for FEMA Counter-UAS grant funding",
    why="Federal funding to deploy approved detection (and, where authorized, mitigation) capability.",
    where_to_submit="FEMA Grant Programs Directorate — FEMA-GPD-GrantPrograms@fema.dhs.gov",
    url="https://www.fema.gov/grants",
)
_SAFER_SKIES_CERT = DocumentationPathway(
    title="Pursue SAFER SKIES certification (FBI National Counter-UAS Training Center)",
    why="The federal pathway for state/local/tribal LE to obtain lawful mitigation authority via DOJ training + certification.",
    where_to_submit="DOJ / FBI NCUTC (coordinate through your agency leadership).",
    url="https://www.fbi.gov/investigate/weapons-of-mass-destruction",
)
_TX_DPS = DocumentationPathway(
    title="Report critical-infrastructure overflight to Texas DPS",
    why="Tex. Gov't Code ch. 423 makes UAS operation/surveillance over certain critical-infrastructure sites an offense — supports a state report.",
    where_to_submit="Texas Department of Public Safety (and the iWatch Texas reporting system).",
    url="https://www.dps.texas.gov/section/intelligence-counterterrorism/iwatch-texas",
)
_FAA_COORD = DocumentationPathway(
    title="Establish real-time FAA coordination / deconfliction",
    why="Authorized mitigation requires coordination with FAA and air-traffic deconfliction before any action.",
    where_to_submit="FAA System Operations Security / your established C-UAS coordination channel.",
    url="https://www.faa.gov/uas/resources/c_uas",
)


def generate(profile: Profile, loc: LocationAttributes) -> list[DocumentationPathway]:
    pathways: list[DocumentationPathway] = []

    if profile in _FEDERAL or profile == Profile.STATE_LOCAL_LE_CERTIFIED:
        # Has (some) authority — emphasize coordination + reporting obligations.
        pathways.append(_FAA_COORD)
        pathways.append(_REPORT_FBI)
    else:
        # No mitigation authority — emphasize what to file instead.
        pathways.append(_REPORT_FBI)
        if profile == Profile.STATE_LOCAL_LE_UNCERTIFIED:
            pathways.append(_SAFER_SKIES_CERT)
        if loc.location_flags.get("critical_infrastructure_zone"):
            pathways.append(_FAA_2209)
        pathways.append(_FAA_997)
        pathways.append(_FEMA_GRANT)

    if loc.location_flags.get("critical_infrastructure_zone"):
        pathways.append(_TX_DPS)

    return pathways
