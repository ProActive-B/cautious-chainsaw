import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { Controls } from "./components/Controls";
import { DecisionReportPanel } from "./components/DecisionReportPanel";
import { MapView } from "./components/MapView";
import type { DecisionReport, Layers, Meta } from "./types";

export function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [layers, setLayers] = useState<Layers | null>(null);
  const [profile, setProfile] = useState<string>("");
  const [credibleThreat, setCredibleThreat] = useState(false);
  const [layerVisibility, setLayerVisibility] = useState<Record<string, boolean>>({
    population: true, airspace: true, zones: true, sites: true,
  });
  const [picked, setPicked] = useState<{ lat: number; lon: number } | null>(null);
  const [report, setReport] = useState<DecisionReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Bootstrap meta + layers.
  useEffect(() => {
    Promise.all([api.meta(), api.layers()])
      .then(([m, l]) => {
        setMeta(m);
        setLayers(l);
        if (m.profiles[0]) setProfile(m.profiles[0].id);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const runAssess = useCallback(
    async (lat: number, lon: number, prof: string, threat: boolean) => {
      if (!prof) return;
      setLoading(true);
      setError(null);
      try {
        setReport(await api.assess(prof, lat, lon, threat));
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const onPick = useCallback(
    (lat: number, lon: number) => {
      setPicked({ lat, lon });
      runAssess(lat, lon, profile, credibleThreat);
    },
    [profile, credibleThreat, runAssess],
  );

  // Re-assess when profile / threat toggle changes for the already-picked point.
  useEffect(() => {
    if (picked) runAssess(picked.lat, picked.lon, profile, credibleThreat);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile, credibleThreat]);

  if (error && !meta) return <div className="fatal">Failed to load: {error}</div>;
  if (!meta) return <div className="loading-screen">Loading…</div>;

  return (
    <div className="layout">
      <aside className="sidebar">
        <header className="app-header">
          <h1>CUAS Decision Map</h1>
          <p className="subtitle">Click the map to assess countermeasure options · pilot: Texas</p>
        </header>

        <Controls
          meta={meta}
          profile={profile}
          setProfile={setProfile}
          credibleThreat={credibleThreat}
          setCredibleThreat={setCredibleThreat}
          layerVisibility={layerVisibility}
          setLayerVisibility={setLayerVisibility}
        />

        {loading && <div className="status">Assessing…</div>}
        {error && meta && <div className="status err">{error}</div>}
        {!picked && !report && (
          <div className="hint">Select your authority profile, then click a location on the map.</div>
        )}
        {report && <DecisionReportPanel report={report} />}
      </aside>

      <main className="map-wrap">
        <MapView
          meta={meta}
          layers={layers}
          layerVisibility={layerVisibility}
          onPick={onPick}
        />
      </main>
    </div>
  );
}
