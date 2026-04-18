import { apiJson, apiFetch } from './api';

export interface SymbolProviders {
  twelvedata: boolean;
  yfinance: boolean;
  binance: boolean;
}

export const DEFAULT_PROVIDERS: SymbolProviders = {
  twelvedata: false,
  yfinance: false,
  binance: false,
};

export interface SymbolSearchResult {
  symbol: string;
  name: string;
  asset_type: string | null;
  exchange: string | null;
  providers: SymbolProviders;
}

export async function searchSymbols(
  query: string,
  limit = 20,
  signal?: AbortSignal,
): Promise<SymbolSearchResult[]> {
  const q = query.trim();
  if (!q) return [];
  const params = new URLSearchParams({ q, limit: String(limit) });
  return apiJson<SymbolSearchResult[]>(`/symbols/search?${params.toString()}`, {
    method: 'GET',
    signal,
  });
}

/** Fire-and-forget: tells the backend yfinance just succeeded for this symbol. */
export function markYFinanceSupported(symbol: string): void {
  const sym = symbol.trim().toUpperCase();
  if (!sym) return;
  void apiFetch('/symbols/mark-yfinance', {
    method: 'POST',
    body: JSON.stringify({ symbol: sym }),
  }).catch(() => {
    // Best-effort only — a failure here shouldn't surface to the user.
  });
}
