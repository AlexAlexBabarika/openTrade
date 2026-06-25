import { describe, it, expect } from 'vitest';
import { MAX_UNIVERSE_SYMBOLS, mergeSymbols, parseSymbols } from './universe';

describe('parseSymbols', () => {
  it('splits on whitespace, commas, semicolons and newlines', () => {
    expect(parseSymbols('aapl, msft;goog\nAMZN  tsla')).toEqual([
      'AAPL',
      'MSFT',
      'GOOG',
      'AMZN',
      'TSLA',
    ]);
  });

  it('uppercases and de-duplicates preserving first occurrence order', () => {
    expect(parseSymbols('msft aapl MSFT Aapl')).toEqual(['MSFT', 'AAPL']);
  });

  it('returns empty for blank input', () => {
    expect(parseSymbols('  ,; \n ')).toEqual([]);
  });
});

describe('mergeSymbols', () => {
  it('appends only new symbols', () => {
    expect(mergeSymbols(['AAPL'], 'aapl msft')).toEqual(['AAPL', 'MSFT']);
  });

  it('caps the universe at the backend limit', () => {
    const existing = Array.from(
      { length: MAX_UNIVERSE_SYMBOLS - 1 },
      (_, i) => `S${i}`,
    );
    const merged = mergeSymbols(existing, 'NEW1 NEW2 NEW3');
    expect(merged).toHaveLength(MAX_UNIVERSE_SYMBOLS);
    expect(merged[merged.length - 1]).toBe('NEW1');
  });
});
