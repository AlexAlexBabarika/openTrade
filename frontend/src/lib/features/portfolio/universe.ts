/**
 * Universe input parsing: the builder accepts free-form pasted text (tickers
 * separated by spaces, commas, semicolons, or newlines) and normalizes it to
 * an uppercase, de-duplicated, order-preserving list capped at the backend's
 * symbol limit.
 */

export const MAX_UNIVERSE_SYMBOLS = 50;

/** Normalize free-form ticker text to uppercase unique symbols, in order. */
export function parseSymbols(text: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of text.split(/[\s,;]+/)) {
    const symbol = raw.trim().toUpperCase();
    if (!symbol || seen.has(symbol)) continue;
    seen.add(symbol);
    out.push(symbol);
  }
  return out;
}

/** Merge pasted text into an existing universe, keeping order and the cap. */
export function mergeSymbols(existing: string[], text: string): string[] {
  const merged = [...existing];
  const seen = new Set(existing);
  for (const symbol of parseSymbols(text)) {
    if (seen.has(symbol)) continue;
    if (merged.length >= MAX_UNIVERSE_SYMBOLS) break;
    seen.add(symbol);
    merged.push(symbol);
  }
  return merged;
}
