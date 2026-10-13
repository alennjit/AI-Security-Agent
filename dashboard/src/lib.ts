import type { SecurityEvent } from "./types";

export type Tier = "critical" | "elevated" | "low";

export const TIER_LABEL: Record<Tier, string> = {
  critical: "Critical",
  elevated: "Elevated",
  low: "Low",
};

/** Risk bands on the 1-10 scale used across the project. */
export function tierOf(score: number): Tier {
  if (score >= 8) return "critical";
  if (score >= 5) return "elevated";
  return "low";
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google",
  microsoft: "Microsoft",
  perplexity: "Perplexity",
  mistral: "Mistral",
  xai: "xAI",
  cohere: "Cohere",
};

export function providerLabel(provider: string): string {
  return PROVIDER_LABELS[provider] ?? provider;
}

const CATEGORY_LABELS: Record<string, string> = {
  credential: "Credentials",
  pii: "Personal data",
  confidential_marker: "Confidential markers",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

/** The backend stores naive UTC timestamps; treat a missing zone as UTC. */
export function parseServerTime(iso: string): Date {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`);
}

export function relativeTime(date: Date, now: number = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - date.getTime()) / 1000));
  if (seconds < 45) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days < 7 ? `${days}d ago` : date.toLocaleDateString();
}

/** Count items per key (an item may contribute to several keys), sorted high to low. */
export function countBy(
  events: SecurityEvent[],
  keys: (event: SecurityEvent) => string[],
): [string, number][] {
  const counts = new Map<string, number>();
  for (const event of events) {
    for (const key of keys(event)) {
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}
