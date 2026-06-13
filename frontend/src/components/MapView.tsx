import { useEffect, useRef, useState } from "react";
import maplibregl, { Map as MLMap, Marker, StyleSpecification } from "maplibre-gl";
import { api } from "../api/client";
import type { Layers, Meta } from "../types";

interface Props {
  meta: Meta;
  layers: Layers | null;
  layerVisibility: Record<string, boolean>;
  onPick: (lat: number, lon: number) => void;
}

// Minimal inline OSM raster basemap — no API key, no external style.json.
const BASE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

const AIRCRAFT_REFRESH_MS = 15000;

export function MapView({ meta, layers, layerVisibility, onPick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Init map once.
  useEffect(() => {
    if (mapRef.current || !containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: [meta.default_view.lon, meta.default_view.lat],
      zoom: meta.default_view.zoom,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.on("load", () => {
      map.addSource("aircraft", { type: "geojson", data: emptyFC() });
      addAircraftLayers(map);
      addDataLayers(map, layers);
      setMapLoaded(true);
    });
    map.on("click", (e) => {
      onPick(e.lngLat.lat, e.lngLat.lng);
      if (markerRef.current) markerRef.current.remove();
      markerRef.current = new maplibregl.Marker({ color: "#e63946" }).setLngLat(e.lngLat).addTo(map);
    });
    mapRef.current = map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // (Re)add static data layers when they arrive.
  useEffect(() => {
    const map = mapRef.current;
    if (map && mapLoaded && layers) addDataLayers(map, layers);
  }, [layers, mapLoaded]);

  // Toggle static-layer visibility.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;
    for (const [group, visible] of Object.entries(layerVisibility)) {
      for (const id of LAYER_IDS[group] ?? []) {
        if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
      }
    }
  }, [layerVisibility, layers, mapLoaded]);

  // Live aircraft: poll while enabled; refresh on map move.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;
    const on = layerVisibility.aircraft ?? true;
    for (const id of LAYER_IDS.aircraft) {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    }
    if (!on) return;
    const refresh = () => refreshAircraft(map);
    refresh();
    const iv = window.setInterval(refresh, AIRCRAFT_REFRESH_MS);
    map.on("moveend", refresh);
    return () => {
      window.clearInterval(iv);
      map.off("moveend", refresh);
    };
  }, [layerVisibility.aircraft, mapLoaded]);

  return <div ref={containerRef} className="map" />;
}

const LAYER_IDS: Record<string, string[]> = {
  population: ["population-fill"],
  airspace: ["airspace-fill", "airspace-line"],
  sua: ["sua-fill", "sua-line"],
  zones: ["zones-fill", "zones-line"],
  sites: ["sites-circle"],
  aircraft: ["aircraft-circle", "aircraft-label"],
};

function emptyFC(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

async function refreshAircraft(map: MLMap) {
  const b = map.getBounds();
  try {
    const data = await api.aircraft({
      s: b.getSouth(), w: b.getWest(), n: b.getNorth(), e: b.getEast(),
    });
    const fc: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: data.aircraft
        .filter((a) => !a.on_ground)
        .map((a) => ({
          type: "Feature",
          properties: { callsign: a.callsign ?? a.icao24, alt_ft: a.alt_ft ?? 10000 },
          geometry: { type: "Point", coordinates: [a.lon, a.lat] },
        })),
    };
    const src = map.getSource("aircraft") as maplibregl.GeoJSONSource | undefined;
    if (src) src.setData(fc as never);
  } catch {
    /* feed hiccup — leave previous aircraft in place */
  }
}

function addAircraftLayers(map: MLMap) {
  // Color by altitude: low (overhead, high collateral concern) = red → high = blue.
  map.addLayer({
    id: "aircraft-circle",
    type: "circle",
    source: "aircraft",
    paint: {
      "circle-radius": 5,
      "circle-stroke-width": 1,
      "circle-stroke-color": "#ffffff",
      "circle-color": [
        "interpolate", ["linear"], ["get", "alt_ft"],
        0, "#e5534b", 1500, "#e3b341", 5000, "#2ea043", 12000, "#2b6cb0",
      ],
    },
  });
  map.addLayer({
    id: "aircraft-label",
    type: "symbol",
    source: "aircraft",
    minzoom: 9,
    layout: {
      "text-field": ["get", "callsign"],
      "text-size": 10,
      "text-offset": [0, 1.2],
    },
    paint: { "text-color": "#0f1419", "text-halo-color": "#ffffff", "text-halo-width": 1.2 },
  });
}

function addSource(map: MLMap, id: string, data: GeoJSON.FeatureCollection) {
  const existing = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
  if (existing) existing.setData(data as never);
  else map.addSource(id, { type: "geojson", data: data as never });
}

function addDataLayers(map: MLMap, layers: Layers | null) {
  if (!layers) return;

  addSource(map, "population", layers.population);
  addSource(map, "airspace", layers.airspace);
  addSource(map, "sua", layers.sua);
  addSource(map, "zones", layers.zones);
  addSource(map, "sites", layers.sites);

  if (!map.getLayer("population-fill")) {
    map.addLayer({
      id: "population-fill",
      type: "fill",
      source: "population",
      paint: {
        "fill-color": [
          "interpolate", ["linear"], ["get", "density_per_km2"],
          0, "#1b3b1b", 300, "#6a8f1f", 1000, "#c98a1f", 1600, "#a3261f",
        ],
        "fill-opacity": 0.22,
      },
    }, "aircraft-circle");
  }
  if (!map.getLayer("airspace-fill")) {
    map.addLayer({
      id: "airspace-fill", type: "fill", source: "airspace",
      paint: {
        "fill-color": [
          "match", ["get", "airspace_class"],
          "B", "#2b6cb0", "C", "#7c3aed", "D", "#2c7a7b", "#2b6cb0",
        ],
        "fill-opacity": 0.10,
      },
    }, "aircraft-circle");
    map.addLayer({
      id: "airspace-line", type: "line", source: "airspace",
      paint: { "line-color": "#2b6cb0", "line-width": 1.2 },
    }, "aircraft-circle");
  }
  if (!map.getLayer("sua-fill")) {
    map.addLayer({
      id: "sua-fill", type: "fill", source: "sua",
      paint: { "fill-color": "#b91c1c", "fill-opacity": 0.14 },
    }, "aircraft-circle");
    map.addLayer({
      id: "sua-line", type: "line", source: "sua",
      paint: { "line-color": "#7f1d1d", "line-width": 1, "line-dasharray": [2, 1] },
    }, "aircraft-circle");
  }
  if (!map.getLayer("zones-fill")) {
    map.addLayer({
      id: "zones-fill", type: "fill", source: "zones",
      paint: { "fill-color": "#d97706", "fill-opacity": 0.3 },
    }, "aircraft-circle");
    map.addLayer({
      id: "zones-line", type: "line", source: "zones",
      paint: { "line-color": "#b45309", "line-width": 2 },
    }, "aircraft-circle");
  }
  if (!map.getLayer("sites-circle")) {
    map.addLayer({
      id: "sites-circle", type: "circle", source: "sites",
      paint: {
        "circle-radius": 7, "circle-color": "#7c3aed",
        "circle-stroke-color": "#fff", "circle-stroke-width": 2,
      },
    }, "aircraft-circle");
  }
}
