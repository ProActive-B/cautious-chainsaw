import { useEffect, useRef } from "react";
import maplibregl, { Map as MLMap, Marker, StyleSpecification } from "maplibre-gl";
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

export function MapView({ meta, layers, layerVisibility, onPick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const loadedRef = useRef(false);

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
      loadedRef.current = true;
      addDataLayers(map, layers);
    });
    map.on("click", (e) => {
      onPick(e.lngLat.lat, e.lngLat.lng);
      if (markerRef.current) markerRef.current.remove();
      markerRef.current = new maplibregl.Marker({ color: "#e63946" })
        .setLngLat(e.lngLat)
        .addTo(map);
    });
    mapRef.current = map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // (Re)add data layers when they arrive.
  useEffect(() => {
    const map = mapRef.current;
    if (map && loadedRef.current && layers) addDataLayers(map, layers);
  }, [layers]);

  // Toggle layer visibility.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    for (const [group, visible] of Object.entries(layerVisibility)) {
      for (const id of LAYER_IDS[group] ?? []) {
        if (map.getLayer(id)) {
          map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
        }
      }
    }
  }, [layerVisibility, layers]);

  return <div ref={containerRef} className="map" />;
}

const LAYER_IDS: Record<string, string[]> = {
  population: ["population-fill"],
  airspace: ["airspace-fill", "airspace-line"],
  zones: ["zones-fill", "zones-line"],
  sites: ["sites-circle"],
};

function addSource(map: MLMap, id: string, data: GeoJSON.FeatureCollection) {
  const existing = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
  if (existing) {
    existing.setData(data as never);
  } else {
    map.addSource(id, { type: "geojson", data: data as never });
  }
}

function addDataLayers(map: MLMap, layers: Layers | null) {
  if (!layers) return;

  addSource(map, "population", layers.population);
  addSource(map, "airspace", layers.airspace);
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
        "fill-opacity": 0.25,
      },
    });
  }
  if (!map.getLayer("airspace-fill")) {
    map.addLayer({
      id: "airspace-fill",
      type: "fill",
      source: "airspace",
      paint: { "fill-color": "#2b6cb0", "fill-opacity": 0.12 },
    });
    map.addLayer({
      id: "airspace-line",
      type: "line",
      source: "airspace",
      paint: { "line-color": "#2b6cb0", "line-width": 1.5, "line-dasharray": [2, 1] },
    });
  }
  if (!map.getLayer("zones-fill")) {
    map.addLayer({
      id: "zones-fill",
      type: "fill",
      source: "zones",
      paint: { "fill-color": "#d97706", "fill-opacity": 0.3 },
    });
    map.addLayer({
      id: "zones-line",
      type: "line",
      source: "zones",
      paint: { "line-color": "#b45309", "line-width": 2 },
    });
  }
  if (!map.getLayer("sites-circle")) {
    map.addLayer({
      id: "sites-circle",
      type: "circle",
      source: "sites",
      paint: {
        "circle-radius": 7,
        "circle-color": "#7c3aed",
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 2,
      },
    });
  }
}
