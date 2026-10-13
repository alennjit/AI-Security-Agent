import type { SecurityEvent } from "../types";
import { categoryLabel, countBy, providerLabel } from "../lib";

function Bars({ title, rows }: { title: string; rows: [string, number][] }) {
  const max = Math.max(1, ...rows.map(([, n]) => n));
  return (
    <div className="panel">
      <h2 className="panel__title">{title}</h2>
      {rows.length === 0 ? (
        <p className="muted">No data yet.</p>
      ) : (
        <ul className="bars">
          {rows.map(([label, count]) => (
            <li key={label} className="bars__row">
              <span className="bars__label">{label}</span>
              <span className="bars__track" aria-hidden="true">
                <span className="bars__fill" style={{ width: `${(count / max) * 100}%` }} />
              </span>
              <span className="bars__value">{count}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Breakdown({ events }: { events: SecurityEvent[] }) {
  const providers = countBy(events, (e) => [e.provider]).map(
    ([key, n]) => [providerLabel(key), n] as [string, number],
  );
  const categories = countBy(events, (e) => e.categories).map(
    ([key, n]) => [categoryLabel(key), n] as [string, number],
  );
  return (
    <section className="breakdown" aria-label="Breakdown">
      <Bars title="By AI service" rows={providers} />
      <Bars title="By data type" rows={categories} />
    </section>
  );
}
