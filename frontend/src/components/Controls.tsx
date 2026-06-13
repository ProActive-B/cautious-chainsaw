import type { Meta } from "../types";

interface Props {
  meta: Meta;
  profile: string;
  setProfile: (p: string) => void;
  credibleThreat: boolean;
  setCredibleThreat: (v: boolean) => void;
  layerVisibility: Record<string, boolean>;
  setLayerVisibility: (v: Record<string, boolean>) => void;
}

const LAYER_LABELS: Record<string, string> = {
  aircraft: "Live aircraft (ADS-B)",
  airspace: "Airspace (FAA Class B/C/D)",
  sua: "Special-use airspace",
  population: "Population density",
  zones: "Restricted zones",
  sites: "Pilot site",
};

export function Controls({
  meta, profile, setProfile, credibleThreat, setCredibleThreat,
  layerVisibility, setLayerVisibility,
}: Props) {
  return (
    <div className="controls">
      <label className="field">
        <span>Authority profile</span>
        <select value={profile} onChange={(e) => setProfile(e.target.value)}>
          {meta.profiles.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
      </label>

      <label className="check">
        <input
          type="checkbox"
          checked={credibleThreat}
          onChange={(e) => setCredibleThreat(e.target.checked)}
        />
        <span>Credible threat declared</span>
      </label>

      <div className="layers">
        <span className="layers-title">Map layers</span>
        {Object.keys(LAYER_LABELS).map((key) => (
          <label key={key} className="check small">
            <input
              type="checkbox"
              checked={layerVisibility[key] ?? true}
              onChange={(e) =>
                setLayerVisibility({ ...layerVisibility, [key]: e.target.checked })
              }
            />
            <span>{LAYER_LABELS[key]}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
