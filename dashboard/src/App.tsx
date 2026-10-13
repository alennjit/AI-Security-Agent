import { useCallback, useEffect, useMemo, useState } from "react";
import { API_BASE_URL, fetchEvents } from "./api";
import { Breakdown } from "./components/Breakdown";
import { EventTable } from "./components/EventTable";
import { Summary } from "./components/Summary";
import { providerLabel, tierOf } from "./lib";
import type { SecurityEvent } from "./types";
import "./App.css";

const REFRESH_MS = 10_000;

type RiskFilter = "all" | "critical" | "elevated";

function App() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [auto, setAuto] = useState(true);
  const [risk, setRisk] = useState<RiskFilter>("all");
  const [provider, setProvider] = useState("all");
  const [query, setQuery] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const data = await fetchEvents(signal);
      setEvents(data);
      setError(null);
      setUpdatedAt(new Date());
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    if (!auto) return;
    const timer = window.setInterval(() => void load(), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [auto, load]);

  const providers = useMemo(() => [...new Set(events.map((e) => e.provider))].sort(), [events]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return events.filter((e) => {
      if (risk !== "all" && tierOf(e.risk_score) !== risk) return false;
      if (provider !== "all" && e.provider !== provider) return false;
      if (q && !`${e.host} ${e.client_ip ?? ""} ${e.provider}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [events, risk, provider, query]);

  const filtered = visible.length !== events.length;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="brand__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="none">
              <path d="M12 2.5 4.5 5.5v6c0 5.2 3.4 9.4 7.5 10.5 4.1-1.1 7.5-5.3 7.5-10.5v-6L12 2.5Z"
                fill="var(--brand-tint)" stroke="var(--brand)" strokeWidth="1.6" strokeLinejoin="round" />
              <circle cx="12" cy="11.5" r="2.6" fill="var(--brand)" />
            </svg>
          </span>
          <div>
            <h1>AI Security Agent</h1>
            <p className="muted">Confidential data in AI prompts, caught at the network edge</p>
          </div>
        </div>
        <div className="controls">
          <span className={`live ${error ? "live--down" : auto ? "live--on" : ""}`} role="status">
            <span className="live__dot" aria-hidden="true" />
            {error ? "Backend unreachable" : auto ? "Live" : "Paused"}
            {updatedAt && !error && <span className="muted small"> · updated {updatedAt.toLocaleTimeString()}</span>}
          </span>
          <label className="switch">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
            Auto-refresh
          </label>
          <button type="button" className="btn" onClick={() => void load()}>Refresh</button>
        </div>
      </header>

      {error && (
        <div className="notice" role="alert">
          <strong>Can't load events.</strong> {error}. Is the backend running at <code>{API_BASE_URL}</code>?
        </div>
      )}

      <Summary events={events} loading={loading} />
      <Breakdown events={events} />

      <section className="panel" aria-labelledby="events-heading">
        <div className="panel__head">
          <h2 id="events-heading" className="panel__title">
            Events{filtered && <span className="muted small"> · showing {visible.length} of {events.length}</span>}
          </h2>
          <div className="filters">
            <label>
              <span className="sr-only">Risk level</span>
              <select value={risk} onChange={(e) => setRisk(e.target.value as RiskFilter)}>
                <option value="all">All risk levels</option>
                <option value="critical">Critical (8–10)</option>
                <option value="elevated">Elevated (5–7)</option>
              </select>
            </label>
            <label>
              <span className="sr-only">AI service</span>
              <select value={provider} onChange={(e) => setProvider(e.target.value)}>
                <option value="all">All AI services</option>
                {providers.map((p) => (
                  <option key={p} value={p}>{providerLabel(p)}</option>
                ))}
              </select>
            </label>
            <label>
              <span className="sr-only">Search host or client</span>
              <input type="search" placeholder="Search host or client IP" value={query}
                onChange={(e) => setQuery(e.target.value)} />
            </label>
          </div>
        </div>

        {loading ? (
          <p className="muted">Loading events…</p>
        ) : events.length === 0 ? (
          <div className="empty">
            <p className="strong">No flagged prompts yet</p>
            <p className="muted">When traffic through the proxy contains secrets, credentials or personal data, it appears here.</p>
          </div>
        ) : visible.length === 0 ? (
          <div className="empty">
            <p className="strong">No events match these filters</p>
          </div>
        ) : (
          <EventTable events={visible} />
        )}
      </section>

      <footer className="footer muted small">
        Findings are redacted at the source — prompt text and matched secret values are never stored.
      </footer>
    </div>
  );
}

export default App;
