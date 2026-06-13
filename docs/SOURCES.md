# Sources & provenance

Every legal rule and data layer must trace to an authoritative source with an
"as-of" date. The law here is **perishable** — re-verify before any operational
reliance. Last reviewed: **2026-06-13**.

> ⚠️ This tool is **decision support, not legal advice or authorization.** The
> rules database has NOT been reviewed by counsel. Verify with counsel and
> coordinate with federal authorities before any action.

## Federal authority (mitigation)
| Authority | Citation | URL | As-of | Notes |
|---|---|---|---|---|
| DHS / DOJ covered facilities | 6 U.S.C. § 124n | https://uscode.house.gov/view.xhtml?req=(title:6%20section:124n) | 2026-06-13 | Extended to 2031 via FY2026 NDAA (signed 2025-12-18) |
| DoD covered installations | 10 U.S.C. § 130i | https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title10-section130i | 2026-06-13 | |
| DOE / NNSA | FY2026 NDAA § 3111 | https://www.congress.gov/ | 2026-06-13 | New nuclear-security C-UAS authority |
| SLTT law enforcement (SAFER SKIES) | FY2026 NDAA (Title LXXXVI) | https://www.congress.gov/crs-product/IN12661 | 2026-06-13 | **VERIFY** — DOJ implementing regs were due ~June 2026; scope of approved tech still settling |

## Federal prohibitions (apply to non-authorized parties)
| Prohibition | Citation | URL | As-of |
|---|---|---|---|
| Destruction of aircraft (drones = aircraft) | 18 U.S.C. § 32 | https://www.law.cornell.edu/uscode/text/18/32 | 2026-06-13 |
| Wiretap Act (interception) | 18 U.S.C. § 2511 | https://www.law.cornell.edu/uscode/text/18/2511 | 2026-06-13 |
| Pen/Trap (signaling capture) | 18 U.S.C. § 3121 | https://www.law.cornell.edu/uscode/text/18/3121 | 2026-06-13 |
| Satellite interference | 18 U.S.C. § 1367 | https://www.law.cornell.edu/uscode/text/18/1367 | 2026-06-13 |
| FCC willful interference / jammers | 47 U.S.C. § 333; § 302a | https://www.fcc.gov/enforcement/areas/jammers | 2026-06-13 |
| Interference with aircraft navigation | 49 U.S.C. § 46307 | https://www.law.cornell.edu/uscode/text/49/46307 | 2026-06-13 |
| Federal airspace preemption | 49 U.S.C. § 40103 | https://www.law.cornell.edu/uscode/text/49/40103 | 2026-06-13 |

## Interagency guidance (framing source)
- DOJ/DHS/FAA/FCC **Advisory on the Application of Federal Laws to the
  Acquisition and Use of Technology to Detect and Mitigate UAS** (Aug 2020) —
  https://www.dhs.gov/publication/interagency-legal-advisory-uas-detection-and-mitigation-technologies
- DHS S&T **C-UAS Technology Guide** — https://www.dhs.gov/publication/st-c-uas-technology-guide
- FAA **C-UAS resources** — https://www.faa.gov/uas/resources/c_uas

## Texas (pilot jurisdiction)
| Item | Citation | URL | As-of | Notes |
|---|---|---|---|---|
| UAS operation / surveillance | Tex. Gov't Code ch. 423 | https://statutes.capitol.texas.gov/Docs/GV/htm/GV.423.htm | 2026-06-13 | **VERIFY** post-*NPPA v. McCraw* (5th Cir. 2023) operative text |
| iWatch Texas reporting | Texas DPS | https://www.dps.texas.gov/section/intelligence-counterterrorism/iwatch-texas | 2026-06-13 | |

## Documentation pathways
| Pathway | URL | As-of |
|---|---|---|
| FAA § 2209 fixed-site (proposed Part 74) | https://www.federalregister.gov/documents/2026/05/06/2026-08943/designation-restrict-the-operation-of-unmanned-aircraft-in-close-proximity-to-a-fixed-site-facility | 2026-06-13 (comments closed 2026-07-06) |
| § 99.7 Special Security Instructions | https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-99/subpart-A/section-99.7.html | 2026-06-13 |
| FEMA grants | https://www.fema.gov/grants | 2026-06-13 |
| FBI field offices | https://www.fbi.gov/contact-us/field-offices | 2026-06-13 |

## Data layers (MVP is SAMPLE data; replace in Phase 2)
| Layer | Real source (Phase 2) | Access | License |
|---|---|---|---|
| UAS Facility Maps | FAA UDDS (ArcGIS) | GeoJSON/REST | Public domain |
| Airspace classes / SUA | FAA ADDS (ArcGIS) | GeoJSON/WFS | Public domain |
| TFR / NOTAM | FAA FNS / Aviation Weather API | AIXM→GeoJSON | Public domain (free key) |
| Live aircraft | OpenSky (MVP) / ADS-B Exchange Enterprise | JSON | Mind commercial terms |
| Population | US Census ACS + WorldPop | API + GeoTIFF | Public / CC-BY |
| Buildings | Microsoft US Building Footprints | GeoJSON | ODbL (attribution) |
| Terrain | USGS 3DEP ImageServer | REST/WCS | Public domain |
| Military / CI | FAA SUA + HIFLD successor (DHS GEOINT) | GeoJSON | Public domain |

> The current `backend/data/seed/tx_pilot.json` is **approximate placeholder
> geometry** (center+radius) to exercise the engine end-to-end. It is NOT
> authoritative and must not be used operationally.
