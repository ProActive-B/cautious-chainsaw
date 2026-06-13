// Mirrors the backend pydantic models (app/models.py).

import type { FeatureCollection } from "geojson";

export type Effect = "permitted" | "conditional" | "prohibited";
export type RiskBand = "low" | "medium" | "high" | "n/a";

export interface Citation {
  statute: string;
  source_url: string;
  advisory?: string | null;
}

export interface RiskScore {
  value: number;
  band: RiskBand;
  drivers: string[];
}

export interface CountermeasureAssessment {
  countermeasure: string;
  label: string;
  category: "detection" | "mitigation";
  effect: Effect;
  rationale: string;
  citations: Citation[];
  conditions: string[];
  risk?: RiskScore | null;
}

export interface NearbyAircraft {
  icao24: string;
  callsign?: string | null;
  distance_nm: number;
  altitude_ft_agl?: number | null;
}

export interface LocationAttributes {
  lat: number;
  lon: number;
  place_label: string;
  airspace_class?: string | null;
  uasfm_ceiling_ft?: number | null;
  nearest_airport?: string | null;
  nearest_airport_distance_nm?: number | null;
  population_density_per_km2?: number | null;
  building_density?: "low" | "medium" | "high" | null;
  rf_congestion?: "low" | "medium" | "high" | null;
  location_flags: Record<string, boolean>;
  active_tfr: boolean;
  active_tfr_names: string[];
  nearby_aircraft: NearbyAircraft[];
  notes: string[];
}

export interface DocumentationPathway {
  title: string;
  why: string;
  where_to_submit: string;
  url: string;
  draft_available: boolean;
}

export interface DecisionReport {
  profile: string;
  profile_label: string;
  location: LocationAttributes;
  authority_banner: string;
  permitted: CountermeasureAssessment[];
  conditional: CountermeasureAssessment[];
  prohibited: CountermeasureAssessment[];
  documentation: DocumentationPathway[];
  rules_db_version: string;
  generated_as_of: string;
  disclaimer: string;
}

export interface Meta {
  profiles: { id: string; label: string }[];
  countermeasures: { id: string; label: string }[];
  default_view: { lat: number; lon: number; zoom: number };
  rules_db_version: string;
}

export interface Layers {
  airspace: FeatureCollection;
  sua: FeatureCollection;
  zones: FeatureCollection;
  population: FeatureCollection;
  sites: FeatureCollection;
}

export interface Aircraft {
  icao24: string;
  callsign?: string | null;
  lat: number;
  lon: number;
  alt_ft?: number | null;
  on_ground: boolean;
  track?: number | null;
}

export interface AircraftResponse {
  count: number;
  aircraft: Aircraft[];
}
