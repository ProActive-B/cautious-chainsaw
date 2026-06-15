import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { api } from "../api/client";
import type { CountermeasureAssessment, DecisionReport } from "../types";

function TakQr({ report }: { report: DecisionReport }) {
  const [src, setSrc] = useState("");
  const url =
    `${window.location.origin}/api/tak/datapackage` +
    `?profile=${encodeURIComponent(report.profile)}` +
    `&lat=${report.location.lat}&lon=${report.location.lon}`;
  useEffect(() => {
    QRCode.toDataURL(url, { margin: 1, width: 140 }).then(setSrc).catch(() => setSrc(""));
  }, [url]);
  if (!src) return null;
  return (
    <div className="tak-qr">
      <img src={src} alt="Scan to load this assessment in ATAK" width={140} height={140} />
      <div className="tak-qr-cap">Scan with your phone → downloads the data package → import in ATAK.</div>
    </div>
  );
}

async function exportTak(report: DecisionReport) {
  try {
    const blob = await api.takPackage(report.profile, report.location.lat, report.location.lon);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cuas-assessment.zip";
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    /* ignore export errors */
  }
}

const BAND_CLASS: Record<string, string> = {
  low: "band-low",
  medium: "band-medium",
  high: "band-high",
  "n/a": "band-na",
};

function Assessment({ a }: { a: CountermeasureAssessment }) {
  return (
    <div className="cm-card">
      <div className="cm-head">
        <span className="cm-label">{a.label}</span>
        {a.risk && (
          <span className={`risk-pill ${BAND_CLASS[a.risk.band]}`}>
            risk {a.risk.value} · {a.risk.band}
          </span>
        )}
      </div>
      <div className="cm-rationale">{a.rationale}</div>
      {a.conditions.length > 0 && (
        <div className="cm-conditions">
          <strong>Conditions:</strong> {a.conditions.join(", ")}
        </div>
      )}
      {a.risk && a.risk.drivers.length > 0 && (
        <div className="cm-drivers">Risk drivers: {a.risk.drivers.join("; ")}</div>
      )}
      {a.citations.length > 0 && (
        <div className="cm-cites">
          {a.citations.map((c, i) => (
            <a key={i} href={c.source_url} target="_blank" rel="noreferrer" title={c.advisory ?? ""}>
              {c.statute}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

export function DecisionReportPanel({ report }: { report: DecisionReport }) {
  const loc = report.location;
  return (
    <div className="report">
      <div className="banner">{report.authority_banner}</div>

      <button className="tak-btn" onClick={() => exportTak(report)} title="Download a TAK data package (ATAK/WinTAK)">
        ⤓ Export to TAK (ATAK/WinTAK)
      </button>
      <TakQr report={report} />

      <div className="loc-summary">
        <div className="loc-title">{loc.place_label}</div>
        <div className="loc-grid">
          <span>Airspace: <b>{loc.airspace_class ?? "—"}</b></span>
          <span>Nearest airport: <b>{loc.nearest_airport ?? "—"}{loc.nearest_airport_distance_nm != null ? ` (${loc.nearest_airport_distance_nm} nm)` : ""}</b></span>
          <span>Pop. density: <b>{loc.population_density_per_km2 != null ? `${loc.population_density_per_km2}/km²` : "—"}</b></span>
          <span>Buildings: <b>{loc.building_density ?? "—"}{loc.building_count != null ? ` (${loc.building_count})` : ""}</b></span>
          <span>RF congestion: <b>{loc.rf_congestion ?? "—"}</b></span>
          <span>Terrain: <b>{loc.terrain ?? "—"}{loc.elevation_m != null ? ` · ${loc.elevation_m} m` : ""}{loc.high_ground ? " · high ground" : ""}</b></span>
          {Object.keys(loc.location_flags).length > 0 && (
            <span className="full">Zone flags: <b>{Object.keys(loc.location_flags).join(", ")}</b></span>
          )}
          {loc.active_tfr && <span className="full warn">Active TFR: {loc.active_tfr_names.join(", ")}</span>}
          {loc.nearby_aircraft.length > 0 && (
            <span className="full warn">{loc.nearby_aircraft.length} aircraft within range</span>
          )}
        </div>
      </div>

      <Section title="Permitted" cls="sec-permitted" items={report.permitted} empty="No fully-permitted options at this location/profile." />
      <Section title="Conditional — requires the listed conditions" cls="sec-conditional" items={report.conditional} empty="No conditional options." />
      <Section title="Prohibited" cls="sec-prohibited" items={report.prohibited} empty="Nothing categorically prohibited for this profile here." />

      <div className="docs">
        <h3>Documentation &amp; coordination pathway</h3>
        {report.documentation.map((d, i) => (
          <div key={i} className="doc-card">
            <a href={d.url} target="_blank" rel="noreferrer" className="doc-title">{d.title}</a>
            <div className="doc-why">{d.why}</div>
            <div className="doc-where"><strong>Submit to:</strong> {d.where_to_submit}</div>
            {d.draft_available && <span className="doc-draft">draft available</span>}
          </div>
        ))}
      </div>

      <div className="footer">
        <div className="disclaimer">{report.disclaimer}</div>
        <div className="provenance">
          Rules DB {report.rules_db_version} · generated {report.generated_as_of}
        </div>
      </div>
    </div>
  );
}

function Section({
  title, cls, items, empty,
}: { title: string; cls: string; items: CountermeasureAssessment[]; empty: string }) {
  return (
    <div className={`section ${cls}`}>
      <h3>{title} <span className="count">{items.length}</span></h3>
      {items.length === 0 ? (
        <div className="empty">{empty}</div>
      ) : (
        items.map((a) => <Assessment key={a.countermeasure} a={a} />)
      )}
    </div>
  );
}
