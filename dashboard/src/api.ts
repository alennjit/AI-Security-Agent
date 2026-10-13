import type { SecurityEvent } from "./types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchEvents(signal?: AbortSignal): Promise<SecurityEvent[]> {
  const response = await fetch(`${API_BASE_URL}/events?limit=500`, { signal });
  if (!response.ok) {
    throw new Error(`Backend returned ${response.status} for /events`);
  }
  return (await response.json()) as SecurityEvent[];
}
