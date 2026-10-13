/** A redacted DLP event as returned by the backend. Never contains prompt text or raw matches. */
export interface SecurityEvent {
  id: number;
  host: string;
  provider: string;
  surface: string;
  risk_score: number;
  rationale: string;
  categories: string[];
  finding_count: number;
  client_ip: string | null;
  created_at: string;
}
