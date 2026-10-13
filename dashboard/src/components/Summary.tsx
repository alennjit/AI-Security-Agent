import type { SecurityEvent } from "../types";
import { tierOf } from "../lib";

interface Tile {
  key: string;
  label: string;
  value: number;
  hint: string;
  tone: "brand" | "critical" | "elevated" | "teal";
}

export function Summary({ events, loading }: { events: SecurityEvent[]; loading: boolean }) {
  const critical = events.filter((e) => tierOf(e.risk_score) === "critical").length;
  const elevated = events.filter((e) => tierOf(e.risk_score) === "elevated").length;
  const devices = new Set(events.map((e) => e.client_ip).filter(Boolean)).size;

  const tiles: Tile[] = [
    { key: "total", label: "Flagged prompts", value: events.length, hint: "all time", tone: "brand" },
    { key: "critical", label: "Critical", value: critical, hint: "risk 8–10", tone: "critical" },
    { key: "elevated", label: "Elevated", value: elevated, hint: "risk 5–7", tone: "elevated" },
    { key: "devices", label: "Devices involved", value: devices, hint: "distinct clients", tone: "teal" },
  ];

  return (
    <section className="tiles" aria-label="Summary">
      {tiles.map((tile) => (
        <div key={tile.key} className={`tile tile--${tile.tone}`}>
          <span className="tile__label">{tile.label}</span>
          <span className="tile__value">{loading ? "–" : tile.value}</span>
          <span className="tile__hint">{tile.hint}</span>
        </div>
      ))}
    </section>
  );
}
