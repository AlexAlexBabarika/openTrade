declare global {
  interface Window {
    __API_BASE__?: string;
  }
}

/**
 * Backend URL. Override at runtime by setting window.__API_BASE__ before app init,
 * or fall back to same-origin /api when served by FastAPI, or localhost for dev.
 */
export const API_BASE =
  typeof window !== 'undefined' &&
    window.__API_BASE__
    ? window.__API_BASE__
    : '';

export function wsStreamUrl(symbol: string): string {
  let base = API_BASE;
  if (!base && typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    base = `${proto}//${window.location.host}`;
  } else if (base) {
    base = base.replace(/^http/, 'ws');
  }
  return `${base}/ws/stream/${encodeURIComponent(symbol)}`;
}

export function yfinanceUrl(
  symbol: string,
  period = '1mo',
  interval = '1d',
): string {
  const params = new URLSearchParams({ period, interval });
  return `${API_BASE}/data/yfinance/${encodeURIComponent(symbol)}?${params}`;
}

export function smaUrl(symbol: string, period = '20'): string {
  return `${API_BASE}/data/indicators/sma?symbol=${encodeURIComponent(symbol)}&period=${period}`;
}
