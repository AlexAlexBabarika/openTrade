import { describe, it, expect } from 'vitest';
import { COMPARISON_PALETTE, nextUnusedColor } from './comparisonPalette';

describe('nextUnusedColor', () => {
  it('returns first palette colour when none used', () => {
    expect(nextUnusedColor([])).toBe(COMPARISON_PALETTE[0]);
  });

  it('skips colours already in use', () => {
    expect(nextUnusedColor([COMPARISON_PALETTE[0]])).toBe(
      COMPARISON_PALETTE[1],
    );
    expect(
      nextUnusedColor([COMPARISON_PALETTE[0], COMPARISON_PALETTE[1]]),
    ).toBe(COMPARISON_PALETTE[2]);
  });

  it('matches case-insensitively', () => {
    expect(nextUnusedColor([COMPARISON_PALETTE[0].toLowerCase()])).toBe(
      COMPARISON_PALETTE[1],
    );
  });

  it('picks freed slot, not the next sequential index', () => {
    const used = COMPARISON_PALETTE.slice(1);
    expect(nextUnusedColor(used)).toBe(COMPARISON_PALETTE[0]);
  });

  it('cycles to index 0 when palette is exhausted', () => {
    expect(nextUnusedColor([...COMPARISON_PALETTE])).toBe(
      COMPARISON_PALETTE[0],
    );
  });
});
