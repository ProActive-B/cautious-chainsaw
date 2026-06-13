import type { DecisionReport, Layers, Meta } from "../types";

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => getJSON<Meta>("/api/meta"),
  layers: () => getJSON<Layers>("/api/layers"),
  assess: async (
    profile: string,
    lat: number,
    lon: number,
    credibleThreat: boolean,
  ): Promise<DecisionReport> => {
    const res = await fetch("/api/assess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, lat, lon, credible_threat: credibleThreat }),
    });
    if (!res.ok) throw new Error(`assess -> ${res.status}`);
    return res.json() as Promise<DecisionReport>;
  },
};
