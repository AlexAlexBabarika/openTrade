/**
 * Backend URL. In Electron/Tauri use env or default to localhost.
 */
export const API_BASE =
  typeof window !== "undefined" && (window as unknown as { __API_BASE__?: string }).__API_BASE__ != null
    ? (window as unknown as { __API_BASE__: string }).__API_BASE__
    : "http://127.0.0.1:8000";

export function wsStreamUrl(symbol: string): string {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/ws/stream/${encodeURIComponent(symbol)}`;
}

export function yfinanceUrl(symbol: string, period = "1mo", interval = "1d"): string {
  const params = new URLSearchParams({ period, interval });
  return `${API_BASE}/data/yfinance/${encodeURIComponent(symbol)}?${params}`;
}

export function smaUrl(symbol: string, period = "20"): string {
  return `${API_BASE}/data/indicators/sma?symbol=${encodeURIComponent(symbol)}&period=${period}`;
}
