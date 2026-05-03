import { describe, it, expect } from 'vitest';
import { resolveComparisonProvider } from './comparisonController.svelte';

describe('resolveComparisonProvider', () => {
  it('reuses main provider when it supports the comparison symbol', () => {
    expect(
      resolveComparisonProvider('binance', {
        binance: true,
        yfinance: true,
        twelvedata: false,
      }),
    ).toBe('binance');
  });

  it('falls back through binance > yfinance > twelvedata', () => {
    expect(
      resolveComparisonProvider('twelvedata', {
        binance: false,
        yfinance: true,
        twelvedata: false,
      }),
    ).toBe('yfinance');

    expect(
      resolveComparisonProvider('yfinance', {
        binance: false,
        yfinance: false,
        twelvedata: true,
      }),
    ).toBe('twelvedata');
  });

  it('returns null when no provider supports the symbol', () => {
    expect(
      resolveComparisonProvider('yfinance', {
        binance: false,
        yfinance: false,
        twelvedata: false,
      }),
    ).toBeNull();
  });

  it('falls back to main provider (non-csv) when providers map is unknown', () => {
    expect(resolveComparisonProvider('yfinance', null)).toBe('yfinance');
  });

  it('returns null when main provider is csv and providers map is unknown', () => {
    expect(resolveComparisonProvider('csv', null)).toBeNull();
  });
});
